CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;

CREATE SCHEMA IF NOT EXISTS ci_recall;

CREATE TABLE ci_recall.pipeline_runs (
  started_at       TIMESTAMPTZ NOT NULL,
  completed_at     TIMESTAMPTZ,
  run_id           BIGINT      NOT NULL,
  run_attempt      INTEGER     NOT NULL,
  repo             TEXT        NOT NULL,
  workflow         TEXT        NOT NULL,
  branch           TEXT        NOT NULL,
  head_sha         TEXT        NOT NULL,
  commit_message   TEXT,
  commit_at        TIMESTAMPTZ,
  event            TEXT        NOT NULL,
  conclusion       TEXT,
  duration_seconds INTEGER,
  html_url         TEXT        NOT NULL,
  UNIQUE (run_id, run_attempt, started_at)
) WITH (
  tsdb.hypertable,
  tsdb.partition_column = 'started_at',
  tsdb.segmentby = 'workflow',
  tsdb.orderby = 'started_at DESC'
);

CREATE TABLE ci_recall.pipeline_jobs (
  started_at       TIMESTAMPTZ NOT NULL,
  completed_at     TIMESTAMPTZ,
  job_id           BIGINT      NOT NULL,
  run_id           BIGINT      NOT NULL,
  run_attempt      INTEGER     NOT NULL,
  workflow         TEXT        NOT NULL,
  branch           TEXT        NOT NULL,
  job_name         TEXT        NOT NULL,
  conclusion       TEXT,
  duration_seconds INTEGER,
  html_url         TEXT,
  UNIQUE (job_id, started_at)
) WITH (
  tsdb.hypertable,
  tsdb.partition_column = 'started_at',
  tsdb.segmentby = 'job_name',
  tsdb.orderby = 'started_at DESC'
);

CREATE TABLE ci_recall.pipeline_steps (
  started_at       TIMESTAMPTZ NOT NULL,
  completed_at     TIMESTAMPTZ,
  job_id           BIGINT      NOT NULL,
  run_id           BIGINT      NOT NULL,
  run_attempt      INTEGER     NOT NULL,
  workflow         TEXT        NOT NULL,
  branch           TEXT        NOT NULL,
  job_name         TEXT        NOT NULL,
  step_number      INTEGER     NOT NULL,
  step_name        TEXT        NOT NULL,
  conclusion       TEXT,
  duration_seconds INTEGER,
  UNIQUE (job_id, step_number, started_at)
) WITH (
  tsdb.hypertable,
  tsdb.partition_column = 'started_at',
  tsdb.segmentby = 'step_name',
  tsdb.orderby = 'started_at DESC'
);

CREATE TABLE ci_recall.failure_logs (
  failed_at   TIMESTAMPTZ NOT NULL,
  job_id      BIGINT      NOT NULL,
  run_id      BIGINT      NOT NULL,
  run_attempt INTEGER     NOT NULL,
  workflow    TEXT        NOT NULL,
  branch      TEXT        NOT NULL,
  head_sha    TEXT        NOT NULL,
  job_name    TEXT        NOT NULL,
  step_name   TEXT,
  excerpt     TEXT        NOT NULL,
  embedding   VECTOR(384) NOT NULL,
  UNIQUE (job_id, failed_at)
) WITH (
  tsdb.hypertable,
  tsdb.partition_column = 'failed_at'
);

CALL remove_columnstore_policy('ci_recall.failure_logs');

CREATE INDEX failure_logs_embedding_idx ON ci_recall.failure_logs
  USING diskann (embedding vector_cosine_ops);

CREATE TABLE ci_recall.deployments (
  deployed_at       TIMESTAMPTZ NOT NULL,
  deployment_id     BIGINT      NOT NULL,
  run_id            BIGINT,
  environment       TEXT        NOT NULL,
  head_sha          TEXT        NOT NULL,
  commit_at         TIMESTAMPTZ NOT NULL,
  lead_time_seconds INTEGER GENERATED ALWAYS AS (EXTRACT(EPOCH FROM deployed_at - commit_at)::INTEGER) STORED,
  UNIQUE (deployment_id, deployed_at)
) WITH (
  tsdb.hypertable,
  tsdb.partition_column = 'deployed_at'
);

CREATE MATERIALIZED VIEW ci_recall.step_durations_daily
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
  time_bucket(INTERVAL '1 day', started_at) AS day,
  workflow,
  job_name,
  step_name,
  count(*)                          AS runs,
  avg(duration_seconds)             AS avg_seconds,
  max(duration_seconds)             AS max_seconds,
  percentile_agg(duration_seconds)  AS duration_percentiles
FROM ci_recall.pipeline_steps
WHERE duration_seconds IS NOT NULL
GROUP BY day, workflow, job_name, step_name
WITH NO DATA;

SELECT add_continuous_aggregate_policy('ci_recall.step_durations_daily',
  start_offset      => INTERVAL '30 days',
  end_offset        => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour');
