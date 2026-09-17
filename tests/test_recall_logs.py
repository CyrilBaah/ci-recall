from recall.logs import error_excerpt, mask_secrets

FAILED_JOB_LOG = """﻿2026-09-17T01:07:51.1000000Z ##[group]Run actions/checkout@v7
2026-09-17T01:07:51.2000000Z Syncing repository: CyrilBaah/ci-recall
2026-09-17T01:07:52.0000000Z ##[endgroup]
2026-09-17T01:07:55.0000000Z ##[group]Run pytest -v
2026-09-17T01:07:55.0100000Z pytest -v
2026-09-17T01:07:55.0200000Z shell: /usr/bin/bash -e {0}
2026-09-17T01:07:55.0300000Z ##[endgroup]
2026-09-17T01:07:56.0000000Z \x1b[1m============ FAILURES ============\x1b[0m
2026-09-17T01:07:56.1000000Z >       assert body["total_readable"] == "5h 1m"
2026-09-17T01:07:56.2000000Z E       AssertionError: assert '5h 61m' == '5h 1m'
2026-09-17T01:07:56.3000000Z FAILED tests/test_episodes.py::test_stats_per_genre
2026-09-17T01:07:56.4000000Z ##[error]Process completed with exit code 1.
2026-09-17T01:07:56.5000000Z Post job cleanup.
"""


def test_excerpt_keeps_failing_step_output_and_error():
    excerpt = error_excerpt(FAILED_JOB_LOG)
    assert excerpt.splitlines() == [
        "============ FAILURES ============",
        '>       assert body["total_readable"] == "5h 1m"',
        "E       AssertionError: assert '5h 61m' == '5h 1m'",
        "FAILED tests/test_episodes.py::test_stats_per_genre",
        "Process completed with exit code 1.",
    ]


def test_excerpt_without_error_marker_uses_last_lines():
    log = "2026-09-17T01:00:00.0Z line one\n2026-09-17T01:00:01.0Z ##[group]Run x\n2026-09-17T01:00:02.0Z line two\n"
    assert error_excerpt(log) == "line one\nline two"


def test_secrets_are_masked():
    text = "connect postgresql://user:pass@host:5432/db token=abc123 ghp_abcdefghijklmnopqrstuvwxyz0123"
    masked = mask_secrets(text)
    assert "pass@host" not in masked
    assert "abc123" not in masked
    assert "ghp_" not in masked
