CREATE ROLE ci_recall_collector LOGIN PASSWORD :'collector_password';
GRANT USAGE ON SCHEMA ci_recall TO ci_recall_collector;
GRANT INSERT ON ci_recall.pipeline_runs, ci_recall.pipeline_jobs, ci_recall.pipeline_steps,
                ci_recall.failure_logs, ci_recall.deployments
  TO ci_recall_collector;
ALTER ROLE ci_recall_collector SET statement_timeout = '30s';

CREATE ROLE ci_recall_reader LOGIN PASSWORD :'reader_password';
GRANT USAGE ON SCHEMA ci_recall TO ci_recall_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ci_recall TO ci_recall_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA ci_recall GRANT SELECT ON TABLES TO ci_recall_reader;
ALTER ROLE ci_recall_reader SET default_transaction_read_only = on;
ALTER ROLE ci_recall_reader SET statement_timeout = '10s';
