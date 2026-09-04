"""Tests for the repo-wide secret content gate.

A detector that quietly stops detecting is worse than no detector, so these
cover both halves: it must catch the real formats, and it must stay silent on
the things this repo legitimately contains (cassette prompt hashes, git SHAs,
Docker cache keys, gist ids, and identifier names that merely read like
credential words).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCANNER = Path(__file__).resolve().parents[2] / "tools" / "scan_secrets.py"
_spec = importlib.util.spec_from_file_location("scan_secrets", _SCANNER)
assert _spec and _spec.loader
scan_secrets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan_secrets)


# Sample credentials for the "must catch" cases. Each marker must stay on its
# own line -- the gate exempts per line, and black reflows long inline lists.
SAMPLE_OPENAI = "sk-Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9"  # pragma: allowlist secret
SAMPLE_GITLAB = "glpat-Aa1Bb2Cc3Dd4Ee5Ff6"  # pragma: allowlist secret
SAMPLE_GITHUB = "ghp_Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9Jj0Kk1Ll2"  # pragma: allowlist secret
SAMPLE_AWS = "AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
SAMPLE_HEX = "4d6ccb1f2e3a4b5c6d7e8f9a0b1c2d3e"  # pragma: allowlist secret
SAMPLE_PASSWORD = "s3cr3tvalue"  # pragma: allowlist secret
SAMPLE_PEM_HEADER = "-----BEGIN RSA PRIVATE KEY-----"  # pragma: allowlist secret
# Built by concatenation so no literal credential-in-URL appears in this file.
SAMPLE_GITLAB_URL = "https://ai_web:" + SAMPLE_GITLAB + "@gitlab.example.com/x"
SAMPLE_HTTP_URL = "https://user:" + SAMPLE_PASSWORD + "@github.com/x.git"


def _findings(text: str) -> list[str]:
    """Scan a snippet as if it were a tracked file."""
    return scan_secrets.scan_text(Path("sample.txt"), text)


# --- must catch -------------------------------------------------------------


def test_catches_a_filter_repo_replacement_mapping() -> None:
    """The case that motivated the gate.

    ``git filter-repo --replace-text`` mapping files put the literal secret on
    the left of ``==>``. Such a file was committed under the obvious name
    ``purge_secrets_history.sh`` and passed a review that only checked paths.
    """
    text = "xu3wm_notarealtokenAG==>***REMOVED-GITLAB-CREDENTIAL***\n"
    assert any("secret replacement mapping" in f for f in _findings(text))


@pytest.mark.parametrize(
    "snippet,rule",
    [
        (f"OPENAI_KEY = '{SAMPLE_OPENAI}'", "openai key"),
        (f"clone {SAMPLE_GITLAB_URL}", "gitlab token"),
        (f"token: {SAMPLE_GITHUB}", "github token"),
        (f"aws: {SAMPLE_AWS}", "aws access key"),
        (SAMPLE_PEM_HEADER, "private key block"),
        (f"git clone {SAMPLE_HTTP_URL}", "credential in url"),
        (f"azure_proxy_key={SAMPLE_HEX}", "hex secret in credential context"),
    ],
)
def test_catches_known_credential_formats(snippet: str, rule: str) -> None:
    """Each provider format must be detected."""
    assert any(rule in f for f in _findings(snippet)), f"{rule} not flagged in {snippet!r}"


def test_findings_never_reprint_the_secret() -> None:
    """CI logs are public; a finding must redact the value it found."""
    secret = SAMPLE_OPENAI
    findings = _findings(f"key = '{secret}'")
    assert findings
    for finding in findings:
        assert secret not in finding
        assert "len=" in finding


# --- must stay silent -------------------------------------------------------


@pytest.mark.parametrize(
    "snippet",
    [
        # Cassette prompt hashes and manifest digests are SHA-256 of prompt text.
        '"digest": "64cff63fe6211810e46af43549f7780049a21796020508ef86b932304e3d87a4"',
        # environment/Dockerfile's Code Ocean cache key.
        "# hash:sha256:f4fac895501ee6cd20b61678a2957bef9fc35e9a066d6217cd8f30df82d7e62b",
        # A pinned git dependency in requirements.txt.
        "aiweb-common @ git+https://github.com/org/llm_utils.git@3d7abc67a50cbee3a9a7fdba57",
        # A gist id inside a source comment.
        "## Adapted from: https://gist.github.com/tommy/ec3c57761f3846c339de925b66f4ac1b",
        # Identifier names that contain credential words.
        "LLM_API_KEY_ENV = ('LLM_API_KEY', 'OPENAI_COMPATIBLE_KEY')",
        "DEMO_SECRET_PLACEHOLDER = 'demo-mode-unused'",
        "monkeypatch.setattr('tiktoken.encoding_for_model', fake)",
        "AZURE_ENDPOINT = require_secret('azure_proxy_endpoint')",
        # Compose secret file references are paths, not values.
        "      file: ./secrets/libkey_api_key",
        # An unfilled template.
        "azure_proxy_key=PUT_YOUR_API_KEY_HERE",
    ],
)
def test_stays_silent_on_legitimate_content(snippet: str) -> None:
    """False positives make a gate get disabled, so these must not fire."""
    assert _findings(snippet) == [], f"false positive on {snippet!r}"


def test_allowlist_marker_exempts_a_line() -> None:
    """Deliberate test fixtures opt out explicitly, on the line itself."""
    line = f"secret = '{SAMPLE_OPENAI}'"
    assert _findings(line)
    assert _findings(f"{line}  # {scan_secrets.ALLOWLIST_MARKER}") == []


def test_the_repository_itself_is_clean() -> None:
    """The gate must pass on the tree it guards, or nobody will keep it green."""
    repo_root = Path(__file__).resolve().parents[2]
    import subprocess

    result = subprocess.run(
        ["python3", str(_SCANNER)], cwd=repo_root, capture_output=True, text=True
    )
    assert result.returncode == 0, f"scanner flagged the repo:\n{result.stderr}"
