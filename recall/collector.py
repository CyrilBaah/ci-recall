"""Record one GitHub Actions workflow run attempt in TimescaleDB.

Only calls the GitHub API and treats logs as data; it never checks out or runs code from the recorded run.
Usage: python -m recall.collector  (reads GITHUB_TOKEN, GITHUB_REPOSITORY, RUN_ID, RUN_ATTEMPT, CI_RECALL_DATABASE_URL)
"""

import os
import time
from datetime import datetime

import certifi
import psycopg2
import requests
from psycopg2.extras import execute_values

from recall.logs import error_excerpt

API = "https://api.github.com"
FAILED = {"failure", "timed_out"}
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class GitHub:
    def __init__(self, token: str, repo: str) -> None:
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get(self, path: str, **params) -> requests.Response:
        for attempt in range(4):
            response = self.session.get(f"{API}/repos/{self.repo}/{path}", params=params, timeout=30)
            if response.status_code not in (404, 500, 502, 503) or attempt == 3:
                response.raise_for_status()
                return response
            time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def run(self, run_id: int, attempt: int) -> dict:
        return self.get(f"actions/runs/{run_id}/attempts/{attempt}").json()

    def jobs(self, run_id: int, attempt: int) -> list[dict]:
        return self.get(f"actions/runs/{run_id}/attempts/{attempt}/jobs", per_page=100).json()["jobs"]

    def job_log(self, job_id: int) -> str:
        return self.get(f"actions/jobs/{job_id}/logs").text

    def deployments(self, sha: str) -> list[dict]:
        return self.get("deployments", sha=sha, environment="production", per_page=100).json()

    def deployment_statuses(self, deployment_id: int) -> list[dict]:
        return self.get(f"deployments/{deployment_id}/statuses", per_page=100).json()


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def seconds_between(start: datetime | None, end: datetime | None) -> int | None:
    return int((end - start).total_seconds()) if start and end and end >= start else None


def collect(github: GitHub, run_id: int, attempt: int) -> dict[str, list[tuple]]:
    run = github.run(run_id, attempt)
    workflow, branch, sha = run["name"], run["head_branch"], run["head_sha"]
    run_started = parse_time(run["run_started_at"])
    run_completed = parse_time(run["updated_at"])
    commit = run.get("head_commit") or {}
    commit_at = parse_time(commit.get("timestamp"))

    rows: dict[str, list[tuple]] = {"runs": [], "jobs": [], "steps": [], "failures": [], "deployments": []}
    rows["runs"].append(
        (
            run_started,
            run_completed,
            run_id,
            attempt,
            github.repo,
            workflow,
            branch,
            sha,
            commit.get("message"),
            commit_at,
            run["event"],
            run["conclusion"],
            seconds_between(run_started, run_completed),
            run["html_url"],
        )
    )

    for job in github.jobs(run_id, attempt):
        job_started = parse_time(job["started_at"]) or run_started
        job_completed = parse_time(job["completed_at"])
        rows["jobs"].append(
            (
                job_started,
                job_completed,
                job["id"],
                run_id,
                attempt,
                workflow,
                branch,
                job["name"],
                job["conclusion"],
                seconds_between(job_started, job_completed),
                job["html_url"],
            )
        )

        failed_step = None
        for step in job.get("steps") or []:
            step_started = parse_time(step["started_at"]) or job_started
            step_completed = parse_time(step["completed_at"])
            rows["steps"].append(
                (
                    step_started,
                    step_completed,
                    job["id"],
                    run_id,
                    attempt,
                    workflow,
                    branch,
                    job["name"],
                    step["number"],
                    step["name"],
                    step["conclusion"],
                    seconds_between(step_started, step_completed),
                )
            )
            if step["conclusion"] in FAILED and failed_step is None:
                failed_step = step["name"]

        if job["conclusion"] in FAILED:
            excerpt = error_excerpt(github.job_log(job["id"]))
            if excerpt:
                failed_at = job_completed or job_started
                rows["failures"].append(
                    [failed_at, job["id"], run_id, attempt, workflow, branch, sha, job["name"], failed_step, excerpt]
                )

    for deployment in github.deployments(sha):
        for status in github.deployment_statuses(deployment["id"]):
            links = f"{status.get('log_url') or ''} {status.get('target_url') or ''}"
            if status["state"] == "success" and f"/runs/{run_id}" in links and commit_at:
                rows["deployments"].append(
                    (parse_time(status["created_at"]), deployment["id"], run_id, "production", sha, commit_at)
                )
                break

    return rows


def embed_failures(rows: dict[str, list]) -> None:
    if not rows["failures"]:
        return
    from fastembed import TextEmbedding

    model = TextEmbedding(EMBEDDING_MODEL)
    texts = [f"{r[7]} / {r[8] or 'unknown step'}: {r[9]}" for r in rows["failures"]]
    for row, vector in zip(rows["failures"], model.passage_embed(texts), strict=True):
        row.append("[" + ",".join(f"{x:.6f}" for x in vector) + "]")


def save(database_url: str, rows: dict[str, list]) -> None:
    statements = {
        "runs": "INSERT INTO ci_recall.pipeline_runs (started_at, completed_at, run_id, run_attempt, repo, workflow, "
        "branch, head_sha, commit_message, commit_at, event, conclusion, duration_seconds, html_url) VALUES %s "
        "ON CONFLICT DO NOTHING",
        "jobs": "INSERT INTO ci_recall.pipeline_jobs (started_at, completed_at, job_id, run_id, run_attempt, workflow, "
        "branch, job_name, conclusion, duration_seconds, html_url) VALUES %s ON CONFLICT DO NOTHING",
        "steps": "INSERT INTO ci_recall.pipeline_steps (started_at, completed_at, job_id, run_id, run_attempt, "
        "workflow, branch, job_name, step_number, step_name, conclusion, duration_seconds) VALUES %s "
        "ON CONFLICT DO NOTHING",
        "failures": "INSERT INTO ci_recall.failure_logs (failed_at, job_id, run_id, run_attempt, workflow, branch, "
        "head_sha, job_name, step_name, excerpt, embedding) VALUES %s ON CONFLICT DO NOTHING",
        "deployments": "INSERT INTO ci_recall.deployments (deployed_at, deployment_id, run_id, environment, head_sha, "
        "commit_at) VALUES %s ON CONFLICT DO NOTHING",
    }
    with psycopg2.connect(database_url, sslrootcert=certifi.where()) as conn, conn.cursor() as cur:
        for table, sql in statements.items():
            if rows[table]:
                execute_values(cur, sql, [tuple(r) for r in rows[table]])
    conn.close()


def record(github: GitHub, database_url: str, run_id: int, attempt: int) -> dict[str, int]:
    rows = collect(github, run_id, attempt)
    embed_failures(rows)
    save(database_url, rows)
    return {table: len(values) for table, values in rows.items()}


def main() -> None:
    github = GitHub(os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
    run_id, attempt = int(os.environ["RUN_ID"]), int(os.environ["RUN_ATTEMPT"])
    counts = record(github, os.environ["CI_RECALL_DATABASE_URL"], run_id, attempt)
    print(f"Recorded run {run_id} attempt {attempt}: {counts}")


if __name__ == "__main__":
    main()
