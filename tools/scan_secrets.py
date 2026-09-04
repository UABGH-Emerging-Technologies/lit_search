#!/usr/bin/env python3
"""Scan every tracked file for secret-shaped content.

This is a content gate, not a filename gate. It exists because a file named
``purge_secrets_history.sh`` -- a git-filter-repo ``--replace-text`` mapping,
whose left-hand sides are the literal secrets -- was committed and passed a
review that only checked staged *paths*.

Deliberately stdlib-only and value-free. It cannot contain the known leaked
values: this script runs in CI, so anything in it is public. Detection is by
format, context, and entropy instead.

Usage:
    python tools/scan_secrets.py            # scan tracked files
    python tools/scan_secrets.py PATH ...   # scan specific paths

Mark an intentional test fixture with ``pragma: allowlist secret`` on the same
line to exempt it.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ALLOWLIST_MARKER = "pragma: allowlist secret"

# Words that make a nearby high-entropy string look like a credential rather
# than a hash, gist id, or commit SHA.
# Word-bounded so "tiktoken" does not read as "token" and
# "azure_proxy_endpoint" does not read as an assignment of "proxy_key".
_CONTEXT = (
    r"(?<![A-Za-z0-9])"
    r"(?:api[_-]?key|secret|token|password|passwd|credential|access[_-]?key|proxy_key)"
    r"(?![A-Za-z])"
)

# (name, pattern, needs_credential_context)
RULES: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    # Provider-specific formats: distinctive enough to flag anywhere.
    ("openai key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), False),
    ("gitlab token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{15,}"), False),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), False),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), False),
    ("slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), False),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), False),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\."), False),
    # Credentials embedded in a URL: https://user:token@host
    ("credential in url", re.compile(r"https?://[A-Za-z0-9_.\-]+:[^@/\s\"']{6,}@"), False),
    # A git-filter-repo --replace-text mapping. The left side of "==>" is by
    # definition the secret being replaced, so such a file is always sensitive.
    # This is the rule that catches the case that motivated this scanner.
    ("secret replacement mapping", re.compile(r"^\s*\S{8,}==>", re.MULTILINE), False),
    # Bare high-entropy values, but only where the line also talks about
    # credentials. Without that guard this fires on cassette prompt hashes,
    # git SHAs, Docker cache keys, and gist ids in comments.
    ("hex secret in credential context", re.compile(r"\b[0-9a-fA-F]{32,}\b"), True),
    # Require a real assignment, not just adjacency, and no "/" or "." so that
    # secrets/libkey_api_key and requirements.in do not read as values.
    (
        "assigned credential",
        re.compile(rf"{_CONTEXT}\s*[:=]\s*[\"']?([A-Za-z0-9+=_\-]{{16,}})"),
        True,
    ),
)

# Entropy floor for the context-dependent rules, to skip things like a line
# reading `api_key = "REPLACE_ME_WITH_YOUR_KEY"`.
MIN_ENTROPY = 3.0

# Obvious non-secrets that show up in templates and docs.
_PLACEHOLDER = re.compile(
    r"(?i)^(your|put|xxx+|todo|change|example|dummy|test|sample|placeholder|redacted|removed|none|null)"
)


def looks_like_identifier(value: str) -> bool:
    """True when a value is plainly a variable name, not a credential.

    Real credentials are opaque. Identifiers carry underscores and a single
    case -- ``azure_proxy_endpoint``, ``LLM_API_KEY_ENV``,
    ``DEMO_SECRET_PLACEHOLDER``. Hex keys never contain an underscore, so this
    separates them cleanly.
    """
    if "_" in value and (value.islower() or value.isupper()):
        return True
    return not (any(c.isdigit() for c in value) and any(c.isalpha() for c in value))


def shannon_entropy(text: str) -> float:
    """Return the Shannon entropy of ``text`` in bits per character."""
    if not text:
        return 0.0
    counts = Counter(text)
    return -sum((n / len(text)) * math.log2(n / len(text)) for n in counts.values())


def tracked_files() -> list[Path]:
    """Return every file git tracks, which is exactly what would be published."""
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, check=True)
    return [Path(name) for name in result.stdout.split("\0") if name]


def scan_text(path: Path, text: str) -> list[str]:
    """Return findings for one file's text.

    Args:
        path: Path used in the finding message.
        text: Full file contents.

    Returns:
        Human-readable findings, each naming file, line, and rule. Matched
        values are redacted -- CI logs are not a place to reprint a secret.
    """
    findings: list[str] = []
    lines = text.splitlines()
    for name, pattern, needs_context in RULES:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = lines[line_no - 1] if line_no <= len(lines) else ""
            if ALLOWLIST_MARKER in line:
                continue
            value = match.group(1) if pattern.groups else match.group(0)
            if needs_context:
                if not re.search(_CONTEXT, line, re.IGNORECASE):
                    continue
                if shannon_entropy(value) < MIN_ENTROPY or _PLACEHOLDER.match(value):
                    continue
                if looks_like_identifier(value):
                    continue
            redacted = f"{value[:4]}…{value[-2:]} (len={len(value)})" if len(value) > 8 else "…"
            findings.append(f"{path}:{line_no}: {name} -> {redacted}")
    return findings


def scan_paths(paths: list[Path]) -> list[str]:
    """Scan the given files, skipping binaries and unreadable entries."""
    findings: list[str] = []
    for path in paths:
        try:
            raw = path.read_bytes()
        except (OSError, IsADirectoryError):
            continue
        if b"\0" in raw[:8192]:  # binary
            continue
        findings.extend(scan_text(path, raw.decode("utf-8", errors="replace")))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Scan tracked files (or the given paths) and fail on any finding.

    Returns:
        ``0`` when clean, ``1`` when anything secret-shaped is found.
    """
    args = sys.argv[1:] if argv is None else argv
    paths = [Path(a) for a in args] if args else tracked_files()
    findings = scan_paths(paths)
    if findings:
        print(f"SECRET-SHAPED CONTENT FOUND ({len(findings)}):", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print(
            f"\nIf a finding is an intentional test fixture, add "
            f"'{ALLOWLIST_MARKER}' to that line.",
            file=sys.stderr,
        )
        return 1
    print(f"no secret-shaped content in {len(paths)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
