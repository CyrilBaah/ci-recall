import re

TIMESTAMP = re.compile(r"^﻿?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z ?")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SECRETS = [
    (re.compile(r"postgres(ql)?://\S+"), "postgresql://***"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "***"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{10,}"), "***"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "***"),
    (re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\s*[=:]\s*\S+"), r"\1=***"),
]
MAX_LINES = 40
MAX_CHARS = 3000


def clean_lines(raw_log: str) -> list[str]:
    """Strip GitHub's per-line timestamps and terminal colour codes."""
    return [ANSI.sub("", TIMESTAMP.sub("", line)).rstrip() for line in raw_log.splitlines()]


def mask_secrets(text: str) -> str:
    for pattern, replacement in SECRETS:
        text = pattern.sub(replacement, text)
    return text


def error_excerpt(raw_log: str) -> str:
    """Return the output of the failing step up to its first error, without the step's command header."""
    lines = clean_lines(raw_log)
    error_at = next((i for i, line in enumerate(lines) if line.startswith("##[error]")), None)
    if error_at is None:
        section = [line for line in lines if line and not line.startswith("##[")][-MAX_LINES:]
    else:
        step_start = max((i for i in range(error_at) if lines[i].startswith("##[group]Run ")), default=0)
        body_start = next(
            (i + 1 for i in range(step_start, error_at) if lines[i].startswith("##[endgroup]")), step_start
        )
        output = [line for line in lines[body_start:error_at] if line and not line.startswith("##[")]
        errors = [line.removeprefix("##[error]") for line in lines[error_at:] if line.startswith("##[error]")]
        section = output[-MAX_LINES:] + errors
    return mask_secrets("\n".join(section))[-MAX_CHARS:]
