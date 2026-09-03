#!/usr/bin/env python3
"""Code Ocean driver for the Lit Search scoping-review pipeline.

Runs the five-step scoping-review workflow entirely in-process through
FastAPI's ``TestClient`` (no uvicorn, no network access to the app itself).
It is intended to be executed headlessly by Code Ocean, which supplies secrets
exclusively as environment variables (Code Ocean User Secrets).

Security contract:
    This module never prints, logs, or persists secret VALUES anywhere. Only
    variable NAMES and presence booleans appear in stdout, exceptions, or the
    run manifest. It never reads ``.env`` files.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Fallback when no research question is supplied.
DEMO_QUESTION: str = (
    "What is the impact of artificial intelligence on perioperative "
    "decision-making and patient outcomes?"
)

# Environment variable names (priority order) used to source LLM credentials.
# Only these NAMES — never their values — may appear in output or the manifest.
LLM_API_KEY_ENV: tuple[str, ...] = ("LLM_API_KEY", "OPENAI_COMPATIBLE_KEY", "azure_proxy_key")
LLM_ENDPOINT_ENV: tuple[str, ...] = (
    "LLM_ENDPOINT",
    "OPENAI_COMPATIBLE_ENDPOINT",
    "azure_proxy_endpoint",
)
LLM_MODEL_ENV: tuple[str, ...] = ("LLM_MODEL", "OPENAI_COMPATIBLE_MODEL")
LLM_MODEL_DEFAULT: str = "gpt-4o"

# Required backend secrets; UPPER_CASE env names are mirrored to the lowercase
# names the app resolves. The app fails fast at import without them
# (ScopingReview_config/app_config.py), so they are validated up front.
FRONTEND_BACKEND_PAIRS: tuple[str, ...] = ("ncbi_api_key", "libkey_api_key")

STEP_LABELS: tuple[tuple[str, str], ...] = (
    ("step1", "initial literature search"),
    ("step2_keywords", "keyword extraction"),
    ("step2_iteration", "iterative refinement"),
    ("step3", "article categorization"),
    ("step4", "summarization"),
    ("step5", "draft generation"),
)


def env_any(*names: str) -> str | None:
    """Return the first non-empty environment value among ``names``.

    Args:
        *names: Environment variable names to inspect, in priority order.

    Returns:
        The first non-empty string whose variable is set, or ``None`` when all
        of the named variables are unset or empty.
    """
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def mirror_upper_to_lower() -> None:
    """Copy UPPER_CASE backend secrets into their lowercase env names.

    The app resolves ``ncbi_api_key`` / ``libkey_api_key`` straight from the
    process environment. When Code Ocean provides them under the UPPERCASE
    name only, this mirrors the value into the lowercase key (only when the
    lowercase key was previously unset). Never prints or logs any value.
    """
    for base in FRONTEND_BACKEND_PAIRS:
        upper = base.upper()
        if not os.environ.get(base, "").strip() and os.environ.get(upper, "").strip():
            os.environ[base] = os.environ[upper]


def read_credentials() -> tuple[str | None, str | None, str]:
    """Read LLM credentials from the environment without side effects.

    Returns:
        A ``(llm_api_key, llm_endpoint, llm_model)`` tuple. The model falls
        back to ``LLM_MODEL_DEFAULT`` when unset; the key and endpoint may be
        ``None`` when their required variables are missing.
    """
    api_key = env_any(*LLM_API_KEY_ENV)
    endpoint = env_any(*LLM_ENDPOINT_ENV)
    model = env_any(*LLM_MODEL_ENV) or LLM_MODEL_DEFAULT
    return api_key, endpoint, model


def missing_required_names() -> list[str]:
    """Describe every unresolved required LLM variable (names only).

    Returns:
        A list of human-readable strings naming the accepted variable names
        for each missing required variable. Empty when everything is present.
    """
    api_key, endpoint, _ = read_credentials()
    missing: list[str] = []
    if api_key is None:
        missing.append("LLM_API_KEY (or OPENAI_COMPATIBLE_KEY, azure_proxy_key)")
    if endpoint is None:
        missing.append("LLM_ENDPOINT (or OPENAI_COMPATIBLE_ENDPOINT, azure_proxy_endpoint)")
    for base in FRONTEND_BACKEND_PAIRS:
        if env_any(base, base.upper()) is None:
            missing.append(f"{base} (or {base.upper()})")
    return missing


def cmd_check_env() -> int:
    """Validate the environment and report status without importing the app.

    Never imports ``app.server`` or ``fastapi``. Prints each missing required
    variable's accepted names (never values); prints ``environment OK`` and
    returns 0 when everything required is present.

    Returns:
        Exit code ``0`` on success, ``1`` if a required variable is missing.
    """
    missing = missing_required_names()
    if missing:
        for name in missing:
            print(f"missing required variable: {name}", file=sys.stderr)
        return 1
    print("environment OK")
    return 0


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _git_commit(repo_root: Path) -> str | None:
    """Return the current HEAD commit hash, or ``None`` on any failure."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:  # noqa: BLE001 - best-effort metadata lookup
        pass
    return None


def _scrub(text: str, api_key: str | None, endpoint: str | None) -> str:
    """Redact the API key and endpoint value from ``text`` (defense in depth)."""
    if api_key:
        text = text.replace(api_key, "***")
    if endpoint:
        text = text.replace(endpoint, "***")
    return text


def resolve_data_dir(repo_root: Path) -> Path:
    """Resolve the directory containing pipeline input data.

    Priority: ``DATA_DIR`` env var, else ``/data`` if it exists (Code Ocean),
    else ``../data`` relative to ``repo_root``.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        The resolved data directory (may not exist yet).
    """
    env_dir = env_any("DATA_DIR")
    if env_dir:
        return Path(env_dir)
    cap_data = Path("/data")
    if cap_data.is_dir():
        return cap_data
    return repo_root.parent / "data"


def resolve_research_question(data_dir: Path) -> str:
    """Resolve the research question for the pipeline.

    Priority: ``RESEARCH_QUESTION`` env var, else the contents of
    ``<data_dir>/research_question.txt``, else ``DEMO_QUESTION``.

    Args:
        data_dir: Resolved pipeline data directory.

    Returns:
        The research question string.
    """
    question = env_any("RESEARCH_QUESTION")
    if question:
        return question
    question_file = data_dir / "research_question.txt"
    if question_file.is_file():
        text = question_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    return DEMO_QUESTION


def load_frozen_step1(data_dir: Path) -> str | None:
    """Return base64 of ``articles.xlsx`` for frozen-corpus mode, else ``None``.

    Args:
        data_dir: Resolved pipeline data directory.

    Returns:
        Base64-encoded bytes of ``<data_dir>/articles.xlsx`` when present,
        otherwise ``None`` (meaning step1 runs live).
    """
    articles = data_dir / "articles.xlsx"
    if not articles.is_file():
        return None
    return base64.b64encode(articles.read_bytes()).decode("ascii")


def write_output(b64: str, dest: Path) -> tuple[Path, str, int]:
    """Decode base64, write bytes to ``dest``, and return metadata.

    Args:
        b64: Base64-encoded file contents.
        dest: Destination path to write the decoded bytes to.

    Returns:
        A ``(path, sha256_hexdigest, size)`` tuple.
    """
    decoded = base64.b64decode(b64)
    dest.write_bytes(decoded)
    digest = hashlib.sha256(decoded).hexdigest()
    return dest, digest, len(decoded)


def record_output(outputs: list[dict[str, Any]], dest: Path, digest: str, size: int) -> None:
    """Append a manifest output entry for a written file."""
    outputs.append({"file": str(dest), "sha256": digest, "bytes": size})


def post(client: Callable, path: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    """POST JSON to the app via TestClient and return the parsed response.

    Args:
        client: The ``fastapi.testclient.TestClient`` instance.
        path: API route to call.
        payload: JSON-serializable request body. The API key is never placed
            here — it travels only in the ``Authorization`` header.
        api_key: LLM API key, sent exclusively in the ``Authorization`` header.

    Returns:
        The parsed JSON response body.

    Raises:
        RuntimeError: If the response status is not 200. The message contains
            only the response text (truncated, key value replaced by ``***``) —
            never the request headers or payload.
    """
    response = client.post(path, json=payload, headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        text = response.text[:2000].replace(api_key, "***")
        raise RuntimeError(f"{path} failed with status {response.status_code}: {text}")
    return response.json()


def _run_pipeline(
    client: Callable,
    results_dir: Path,
    research_question: str,
    user_categories: str,
    api_key: str,
    endpoint: str,
    model: str,
    frozen_b64: str | None,
    outputs: list[dict[str, Any]],
) -> None:
    """Execute the six pipeline calls and write every resulting output file.

    Args:
        client: The ``fastapi.testclient.TestClient`` instance.
        results_dir: Destination directory for all generated files.
        research_question: Research question driving the pipeline.
        user_categories: User-defined categorization directive.
        api_key: LLM API key (Authorization header only).
        endpoint: OpenAI-compatible endpoint URL.
        model: OpenAI-compatible model name.
        frozen_b64: Base64 step1 content when running from a frozen corpus,
            else ``None`` to run the live search.
        outputs: Manifest output list to append entries to.

    Raises:
        RuntimeError: Propagated from step failures; the caller records it.
    """
    step = STEP_LABELS[0][0]
    t0 = time.monotonic()
    if frozen_b64 is not None:
        dest, digest, size = write_output(frozen_b64, results_dir / "step1_search_results.xlsx")
        record_output(outputs, dest, digest, size)
        step1_b64 = frozen_b64
    else:
        payload = {
            "research_question": research_question,
            "openai_compatible_endpoint": endpoint,
            "openai_compatible_model": model,
        }
        data = post(client, "/v01/scoping/step1/", payload, api_key)
        step1_b64 = data["encoded_xlsx"]
        dest, digest, size = write_output(step1_b64, results_dir / "step1_search_results.xlsx")
        record_output(outputs, dest, digest, size)
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")

    step = STEP_LABELS[1][0]
    t0 = time.monotonic()
    payload = {
        "research_question": research_question,
        "openai_compatible_endpoint": endpoint,
        "openai_compatible_model": model,
        "xlsx_encoded": step1_b64,
    }
    data = post(client, "/v01/scoping/step2/keywords/", payload, api_key)
    kw_dest = results_dir / "step2_keywords.json"
    kw_dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    kw_bytes = kw_dest.read_bytes()
    record_output(outputs, kw_dest, hashlib.sha256(kw_bytes).hexdigest(), len(kw_bytes))
    primary = data.get("primary_keywords", [])
    secondary = data.get("secondary_keywords", [])
    exclusion = data.get("exclusion_keywords", [])
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")

    step = STEP_LABELS[2][0]
    t0 = time.monotonic()
    payload = {
        "research_question": research_question,
        "primary_keywords": primary,
        "secondary_keywords": secondary,
        "exclusion_keywords": exclusion,
        "xlsx_encoded": step1_b64,
        "openai_compatible_endpoint": endpoint,
        "openai_compatible_model": model,
    }
    data = post(client, "/v01/scoping/step2/iteration/", payload, api_key)
    step2_b64 = data["encoded_xlsx"]
    dest, digest, size = write_output(step2_b64, results_dir / "step2_refined_results.xlsx")
    record_output(outputs, dest, digest, size)
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")

    step = STEP_LABELS[3][0]
    t0 = time.monotonic()
    payload = {
        "research_question": research_question,
        "openai_compatible_endpoint": endpoint,
        "openai_compatible_model": model,
        "xlsx_encoded": step2_b64,
        "user_defined_categories": user_categories,
    }
    data = post(client, "/v01/scoping/step3/", payload, api_key)
    step3_b64 = data["encoded_xlsx"]
    dest, digest, size = write_output(step3_b64, results_dir / "step3_categorized.xlsx")
    record_output(outputs, dest, digest, size)
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")

    step = STEP_LABELS[4][0]
    t0 = time.monotonic()
    payload = {
        "research_question": research_question,
        "openai_compatible_endpoint": endpoint,
        "openai_compatible_model": model,
        "xlsx_encoded": step3_b64,
    }
    data = post(client, "/v01/scoping/step4/", payload, api_key)
    step4_b64 = data["encoded_docx"]
    dest, digest, size = write_output(step4_b64, results_dir / "step4_summaries.docx")
    record_output(outputs, dest, digest, size)
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")

    step = STEP_LABELS[5][0]
    t0 = time.monotonic()
    payload = {
        "research_question": research_question,
        "openai_compatible_endpoint": endpoint,
        "openai_compatible_model": model,
        "docx_encoded": step4_b64,
    }
    data = post(client, "/v01/scoping/step5/", payload, api_key)
    step5_b64 = data["encoded_docx"]
    dest, digest, size = write_output(step5_b64, results_dir / "step5_draft.docx")
    record_output(outputs, dest, digest, size)
    print(f"[{step}] completed in {time.monotonic() - t0:.1f}s")


def _write_manifest(
    results_dir: Path,
    *,
    started_utc: str,
    finished_utc: str,
    status: str,
    error_info: tuple[str, str] | None,
    outputs: list[dict[str, Any]],
    corpus_source: str,
    research_question: str,
    model: str,
) -> None:
    """Write ``run_manifest.json`` describing one pipeline invocation.

    The manifest contains only presence booleans and variable NAMES for
    credentials — never the API key value or the LLM endpoint URL value.

    Args:
        results_dir: Directory to write the manifest into.
        started_utc: ISO-8601 start timestamp.
        finished_utc: ISO-8601 finish timestamp.
        status: ``"succeeded"`` or ``"failed"``.
        error_info: Optional ``(error_class, scrubbed_message)`` tuple.
        outputs: List of ``{file, sha256, bytes}`` entries.
        corpus_source: ``"frozen"`` or ``"live"``.
        research_question: The research question used.
        model: The LLM model name used.
    """
    manifest: dict[str, Any] = {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "status": status,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(Path(__file__).resolve().parent.parent),
        "llm_model": model,
        "corpus_source": corpus_source,
        "research_question": research_question,
        "llm_endpoint_set": bool(env_any(*LLM_ENDPOINT_ENV)),
        "ncbi_api_key_set": bool(os.environ.get("ncbi_api_key", "").strip()),
        "libkey_api_key_set": bool(os.environ.get("libkey_api_key", "").strip()),
        "outputs": outputs,
    }
    if error_info is not None:
        manifest["error_class"] = error_info[0]
        manifest["error_message"] = error_info[1]
    manifest_path = results_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline driver, validating the environment first.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code ``0`` on success, ``1`` on a pipeline failure or missing
        required environment variable.
    """
    parser = argparse.ArgumentParser(
        description="Run the Lit Search scoping-review pipeline for Code Ocean."
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Validate required environment variables and exit without running the app.",
    )
    args = parser.parse_args(argv)

    mirror_upper_to_lower()

    if args.check_env:
        return cmd_check_env()

    missing = missing_required_names()
    if missing:
        for name in missing:
            print(f"missing required variable: {name}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = resolve_data_dir(repo_root)
    results_dir = Path(env_any("RESULTS_DIR") or "./results")
    results_dir.mkdir(parents=True, exist_ok=True)
    research_question = resolve_research_question(data_dir)
    user_categories = env_any("USER_DEFINED_CATEGORIES") or ""
    api_key, endpoint, model = read_credentials()
    frozen_b64 = load_frozen_step1(data_dir)
    corpus_source = "frozen" if frozen_b64 is not None else "live"

    started_utc = _utc_now()
    status = "succeeded"
    error_info: tuple[str, str] | None = None
    outputs: list[dict[str, Any]] = []

    try:
        # Lazy imports AFTER validation so --check-env never loads the app.
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.server import app  # noqa: PLC0415

        client = TestClient(app)
        _run_pipeline(
            client,
            results_dir,
            research_question,
            user_categories,
            api_key,
            endpoint,
            model,
            frozen_b64,
            outputs,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced via the manifest
        status = "failed"
        error_info = (type(exc).__name__, _scrub(str(exc), api_key, endpoint))
        print(f"pipeline failed: {type(exc).__name__}", file=sys.stderr)
    finally:
        _write_manifest(
            results_dir,
            started_utc=started_utc,
            finished_utc=_utc_now(),
            status=status,
            error_info=error_info,
            outputs=outputs,
            corpus_source=corpus_source,
            research_question=research_question,
            model=model,
        )

    return 0 if status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
