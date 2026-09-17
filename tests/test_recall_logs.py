from recall.logs import error_excerpt, mask_secrets

PYTEST_FAILURE_LOG = """﻿2026-09-17T01:07:51.1000000Z ##[group]Run actions/checkout@v7
2026-09-17T01:07:51.2000000Z Syncing repository: CyrilBaah/ci-recall
2026-09-17T01:07:52.0000000Z ##[endgroup]
2026-09-17T01:07:55.0000000Z ##[group]Run pytest -v
2026-09-17T01:07:55.0100000Z pytest -v
2026-09-17T01:07:55.0200000Z shell: /usr/bin/bash -e {0}
2026-09-17T01:07:55.0300000Z ##[endgroup]
2026-09-17T01:07:55.5000000Z rootdir: /home/runner/work/ci-recall/ci-recall
2026-09-17T01:07:55.6000000Z tests/test_episodes.py::test_get_episode PASSED                          [ 19%]
2026-09-17T01:07:55.7000000Z tests/test_episodes.py::test_format_duration FAILED                      [ 52%]
2026-09-17T01:07:56.0000000Z \x1b[1m========== FAILURES ==========\x1b[0m
2026-09-17T01:07:56.1000000Z >       assert format_duration(45) == "45m"
2026-09-17T01:07:56.2000000Z E       AssertionError: assert '1h 45m' == '45m'
2026-09-17T01:07:56.3000000Z FAILED tests/test_episodes.py::test_format_duration - AssertionError
2026-09-17T01:07:56.4000000Z ##[error]Process completed with exit code 1.
2026-09-17T01:07:56.5000000Z Post job cleanup.
"""

PIP_FAILURE_LOG = """2026-09-17T02:00:00.0000000Z ##[group]Run pip install -r requirements.txt -r requirements-dev.txt
2026-09-17T02:00:00.1000000Z ##[endgroup]
2026-09-17T02:00:01.0000000Z Collecting fastapi==9.9.9 (from -r requirements.txt (line 1))
2026-09-17T02:00:02.0000000Z ERROR: Could not find a version that satisfies the requirement fastapi==9.9.9
2026-09-17T02:00:02.1000000Z ERROR: No matching distribution found for fastapi==9.9.9
2026-09-17T02:00:02.2000000Z ##[error]Process completed with exit code 1.
"""


def test_pytest_excerpt_starts_at_failures_section():
    assert error_excerpt(PYTEST_FAILURE_LOG).splitlines() == [
        "========== FAILURES ==========",
        '>       assert format_duration(45) == "45m"',
        "E       AssertionError: assert '1h 45m' == '45m'",
        "FAILED tests/test_episodes.py::test_format_duration - AssertionError",
        "Process completed with exit code 1.",
    ]


def test_pip_excerpt_keeps_resolver_errors():
    assert error_excerpt(PIP_FAILURE_LOG).splitlines() == [
        "ERROR: Could not find a version that satisfies the requirement fastapi==9.9.9",
        "ERROR: No matching distribution found for fastapi==9.9.9",
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
