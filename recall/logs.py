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
NOISE = re.compile(r" PASSED\b|^(Requirement already satisfied|Collecting |Downloading |Using cached )")
ERROR_SECTION = re.compile(r"^=+ (FAILURES|ERRORS) =+$|^Traceback \(most recent call last\)|^ERROR[: ]")
MAX_LINES = 40
MAX_CHARS = 3000


def clean_lines(raw_log: str) -> list[str]:
    """Strip GitHub's per-line timestamps and terminal colour codes."""
    return [ANSI.sub("", TIMESTAMP.sub("", line)).rstrip() for line in raw_log.splitlines()]


def mask_secrets(text: str) -> str:
    for pattern, replacement in SECRETS:
        text = pattern.sub(replacement, text)
    return text


def focus(output: list[str]) -> list[str]:
    """Drop passing-test and download noise, and start at the error section when there is one."""
    output = [line for line in output if line and not line.startswith("##[") and not NOISE.search(line)]
    start = next((i for i, line in enumerate(output) if ERROR_SECTION.search(line)), None)
    return (output[start:] if start is not None else output)[-MAX_LINES:]


def error_excerpt(raw_log: str) -> str:
    """Return the error output of the failing step, without the step's command header or noise."""
    lines = clean_lines(raw_log)
    error_at = next((i for i, line in enumerate(lines) if line.startswith("##[error]")), None)
    if error_at is None:
        section = focus(lines)
    else:
        step_start = max((i for i in range(error_at) if lines[i].startswith("##[group]Run ")), default=0)
        body_start = next(
            (i + 1 for i in range(step_start, error_at) if lines[i].startswith("##[endgroup]")), step_start
        )
        errors = [line.removeprefix("##[error]") for line in lines[error_at:] if line.startswith("##[error]")]
        section = focus(lines[body_start:error_at]) + errors
    return mask_secrets("\n".join(section))[-MAX_CHARS:]
