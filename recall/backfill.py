"""Record every completed run (and every attempt) of the CI workflow. Safe to run repeatedly.

Usage: python -m recall.backfill  (reads GITHUB_TOKEN, GITHUB_REPOSITORY, CI_RECALL_DATABASE_URL)
"""

import os

from recall.collector import GitHub, record

WORKFLOW_FILE = "ci.yml"


def main() -> None:
    github = GitHub(os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
    database_url = os.environ["CI_RECALL_DATABASE_URL"]
    page = 1
    while True:
        runs = github.get(
            f"actions/workflows/{WORKFLOW_FILE}/runs", status="completed", per_page=100, page=page
        ).json()["workflow_runs"]
        if not runs:
            break
        for run in runs:
            for attempt in range(1, run["run_attempt"] + 1):
                counts = record(github, database_url, run["id"], attempt)
                print(f"Recorded run {run['id']} attempt {attempt}: {counts}")
        page += 1


if __name__ == "__main__":
    main()
