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

# code/run exports PYTHONPATH=/code, but the driver is also invoked directly
# (tests, scripts/record_demo.py), where sys.path[0] is scripts/ instead.
_CODE_ROOT = str(Path(__file__).resolve().parent.parent)
if _CODE_ROOT not in sys.path:
    sys.path.insert(0, _CODE_ROOT)

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

# Run modes. "demo" replays committed fixtures with no credentials and no
# network; "live" calls the real LLM/PubMed/LibKey APIs; "auto" picks live only
# when a complete live credential set is present.
RUN_MODES: tuple[str, ...] = ("auto", "demo", "live")
RUN_MODE_DEFAULT: str = "auto"

# Placeholder values for the two secrets ScopingReview_config/app_config.py
# resolves at import time. In demo mode no network call ever consumes them.
DEMO_SECRET_PLACEHOLDER: str = "demo-mode-unused"

# Categories the demo corpus is sorted into. These MUST be a baked-in default
# rather than an environment variable: they are part of the step-3 prompt, so a
# Reproducible Run that did not set them would build different prompts than the
# recording and miss every categorization call.
DEFAULT_DEMO_CATEGORIES: str = (
    "preoperative risk prediction, intraoperative decision support, "
    "postoperative outcome prediction, clinical implementation and workflow, "
    "model performance and validation"
)

# Articles auto-marked relevant when running unattended. The pipeline gates
# steps 3-5 behind a human screening decision that a headless run cannot make.
DEFAULT_SCREEN_LIMIT: int = 15

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


def cmd_check_env(mode: str, fixture_dir: Path) -> int:
    """Validate the run prerequisites and report status without importing the app.

    Never imports ``app.server`` or ``fastapi``. In demo mode the credential
    check is irrelevant, so this checks that every cassette is present instead.
    In live mode it prints each missing variable's accepted names (never values).

    Args:
        mode: The resolved run mode, ``"demo"`` or ``"live"``.
        fixture_dir: Directory expected to hold the demo cassettes.

    Returns:
        Exit code ``0`` on success, ``1`` if a prerequisite is missing.
    """
    if mode == "demo":
        from capsule.replay import CASSETTE_FILES  # noqa: PLC0415

        absent = [name for name in CASSETTE_FILES if not (fixture_dir / name).is_file()]
        if absent:
            print(f"missing demo fixtures in {fixture_dir}: {', '.join(absent)}", file=sys.stderr)
            print("record them with scripts/record_demo.py", file=sys.stderr)
            return 1
        print(f"demo fixtures OK ({fixture_dir})")
        return 0

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


def resolve_fixture_dir(repo_root: Path) -> Path:
    """Resolve the directory holding the offline demo cassettes.

    Priority: ``LIT_DEMO_FIXTURES`` env var, else ``<repo_root>/demo_fixtures``.

    Unlike the pipeline's data directory this deliberately does NOT fall back to
    ``/data``: Code Ocean provisions ``/data`` from attached Data Assets rather
    than from the repository, so fixtures kept there would not travel with a
    published capsule. They ship inside ``code/`` instead.

    Args:
        repo_root: Absolute path to the repository code root.

    Returns:
        The resolved fixture directory (may not exist yet).
    """
    env_dir = env_any("LIT_DEMO_FIXTURES")
    if env_dir:
        return Path(env_dir)
    return repo_root / "demo_fixtures"


def resolve_mode(requested: str) -> str:
    """Decide whether this run replays fixtures or calls live APIs.

    Args:
        requested: One of ``RUN_MODES``.

    Returns:
        Either ``"demo"`` or ``"live"``.
    """
    if requested != "auto":
        return requested
    return "live" if not missing_required_names() else "demo"


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


def _check_fixture_inputs(fixture_dir: Path, research_question: str, user_categories: str) -> None:
    """Warn when this run's inputs differ from the ones the fixtures were recorded with.

    The research question and the category list are both interpolated into
    prompts, so a mismatch guarantees cassette misses. Saying so up front beats
    letting the run fail several steps later on an opaque hash.

    Args:
        fixture_dir: Directory holding the cassettes.
        research_question: Question this run will use.
        user_categories: Category list this run will use.
    """
    manifest_path = fixture_dir / "fixtures.json"
    if not manifest_path.is_file():
        return
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    for label, current, key in (
        ("research question", research_question, "research_question"),
        ("categories", user_categories, "user_defined_categories"),
    ):
        previous = recorded.get(key)
        if previous is not None and previous != current:
            print(
                f"WARNING: {label} differs from the recording, so every prompt "
                f"containing it will miss.\n  recorded: {previous!r}\n  this run: {current!r}",
                file=sys.stderr,
            )
    if recorded.get("complete") is False:
        print(
            "WARNING: these fixtures are marked incomplete — the recording that "
            "produced them did not finish.",
            file=sys.stderr,
        )


def _assert_categorized(step3_path: Path, auto_screen: int) -> None:
    """Fail at step 3 if nothing was categorized, naming the actual cause.

    Steps 3-5 are gated on human relevance screening. When no article is marked
    relevant, step 3 still returns HTTP 200 but its categorization loop never
    runs, so the ``category`` column is never created and step 4 dies with a
    bare ``KeyError: 'category'`` that says nothing about why.

    Args:
        step3_path: The written step-3 workbook.
        auto_screen: The synthetic-screening count in force for this run.

    Raises:
        RuntimeError: If the workbook has no categorized articles.
    """
    import pandas as pd  # noqa: PLC0415

    frame = pd.read_excel(step3_path)
    categorized = frame["category"].notna().sum() if "category" in frame.columns else 0
    if categorized:
        return

    hint = (
        f"auto-screening was on (--auto-screen {auto_screen}) but still produced no relevant "
        "articles, so the screening marks are not surviving into step 3"
        if auto_screen > 0
        else "auto-screening is off (--auto-screen 0), so no article was ever marked relevant; "
        "pass --auto-screen N for an unattended run, or supply a workbook with reviewer marks"
    )
    raise RuntimeError(
        f"step 3 categorized 0 of {len(frame)} articles — {hint}. "
        "Steps 4 and 5 cannot run without a 'category' column."
    )


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
    *,
    auto_screen: int,
    screening_info: dict[str, Any] | None = None,
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
        auto_screen: When > 0, mark this many step-1 articles as reviewer-relevant
            so the unattended run can pass the human screening gate. Synthetic.
        screening_info: Optional dict populated with what was marked, for the
            run manifest.

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

    if auto_screen > 0:
        # The pipeline expects a human to mark articles Yes between step 1 and
        # step 2. Nobody does that here, so without this every downstream step
        # sees zero relevant articles and step 4 fails on a missing 'category'.
        from capsule.screening import NOTICE, auto_screen_xlsx  # noqa: PLC0415

        step1_b64, marked, total = auto_screen_xlsx(step1_b64, auto_screen)
        notice = NOTICE.format(marked=marked, total=total)
        print(f"WARNING: {notice}", file=sys.stderr)
        (results_dir / "DEMO_NOTICE.txt").write_text(notice + "\n", encoding="utf-8")
        if screening_info is not None:
            screening_info.update({"synthetic": True, "marked": marked, "total": total})

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
    if not user_categories.strip():
        # _prep_categorylist() turns "" into [], so the model is asked to sort
        # articles into no categories at all and invents its own.
        print(
            "WARNING: USER_DEFINED_CATEGORIES is empty, so step 3 categorizes against an "
            "empty category list and step 4 summarizes whatever the model invents. Set it "
            "to a comma-separated list matching your research question for a usable review.",
            file=sys.stderr,
        )
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
    _assert_categorized(dest, auto_screen)
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
    mode: str,
    fixture_digest: str | None = None,
    fixture_counts: dict[str, int] | None = None,
    blocked_network_calls: int | None = None,
    cassette_misses: list[str] | None = None,
    screening: dict[str, Any] | None = None,
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
        mode: ``"demo"`` (offline replay) or ``"live"``.
        fixture_digest: Digest over the replayed cassette keys, demo mode only.
        fixture_counts: Recorded interactions per seam, demo mode only.
        blocked_network_calls: Outbound calls the demo guard intercepted. A
            non-zero value means the run tried to reach the network.
        cassette_misses: Lookups demo mode could not satisfy. Non-empty means
            the fixtures went stale and must be re-recorded.
        screening: Synthetic-screening record. Present means relevance decisions
            in this run were fabricated, not made by human reviewers.
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
        "mode": mode,
    }
    if fixture_digest is not None:
        manifest["fixture_digest"] = fixture_digest
    if fixture_counts is not None:
        manifest["fixture_counts"] = fixture_counts
    if blocked_network_calls is not None:
        manifest["blocked_network_calls"] = blocked_network_calls
    if cassette_misses:
        manifest["cassette_misses"] = cassette_misses
    if screening:
        manifest["screening"] = screening
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
    parser.add_argument(
        "--auto-screen",
        type=int,
        default=None,
        help=(
            "Mark this many step-1 articles reviewer-relevant so an unattended run "
            "can pass the human screening gate (demo/record only). 0 disables. "
            "Default: %d in demo mode, 0 in live mode."
        )
        % DEFAULT_SCREEN_LIMIT,
    )
    parser.add_argument(
        "--mode",
        choices=RUN_MODES,
        default=env_any("LIT_RUN_MODE") or RUN_MODE_DEFAULT,
        help=(
            "'demo' replays committed fixtures offline with no credentials, "
            "'live' calls the real APIs, 'auto' (default) picks live only when "
            "a complete credential set is present."
        ),
    )
    args = parser.parse_args(argv)

    mirror_upper_to_lower()

    repo_root = Path(__file__).resolve().parent.parent
    mode = resolve_mode(args.mode)

    if args.check_env:
        return cmd_check_env(mode, resolve_fixture_dir(repo_root))

    if mode == "live":
        missing = missing_required_names()
        if missing:
            for name in missing:
                print(f"missing required variable: {name}", file=sys.stderr)
            return 1

    data_dir = resolve_data_dir(repo_root)
    results_dir = Path(env_any("RESULTS_DIR") or "./results")
    results_dir.mkdir(parents=True, exist_ok=True)
    research_question = resolve_research_question(data_dir)
    # Demo runs fall back to the baked-in categories so recording and replay
    # always build identical step-3 prompts. Live runs keep the caller's choice.
    user_categories = env_any("USER_DEFINED_CATEGORIES") or (
        DEFAULT_DEMO_CATEGORIES if mode == "demo" else ""
    )
    api_key, endpoint, model = read_credentials()
    frozen_b64 = load_frozen_step1(data_dir)
    corpus_source = "frozen" if frozen_b64 is not None else "live"

    # Live runs default to no synthetic screening: a real run should use real
    # reviewer decisions carried in the uploaded workbook.
    if args.auto_screen is not None:
        auto_screen = args.auto_screen
    else:
        env_value = env_any("LIT_AUTO_SCREEN")
        if env_value is not None:
            auto_screen = int(env_value)
        else:
            auto_screen = DEFAULT_SCREEN_LIMIT if mode == "demo" else 0

    screening_info: dict[str, Any] = {}
    fixture_dir = resolve_fixture_dir(repo_root)
    replay_session = None
    if mode == "demo":
        from capsule import replay as replay_mod  # noqa: PLC0415

        # app_config.py resolves these two at import time and fails fast on an
        # empty value. Nothing in demo mode reaches a network call that would
        # consume them; the doubles intercept every external seam.
        for secret in FRONTEND_BACKEND_PAIRS:
            os.environ.setdefault(secret, DEMO_SECRET_PLACEHOLDER)
        # Short-circuit the SSRF validator's DNS lookup before the network guard
        # would have to intercept it (net_validators checks the allowlist first).
        os.environ.setdefault("LIT_LLM_ENDPOINT_ALLOWLIST", replay_mod.DEMO_ENDPOINT_HOST)
        api_key = DEMO_SECRET_PLACEHOLDER
        endpoint = replay_mod.DEMO_ENDPOINT
        model = replay_mod.DEMO_MODEL

    started_utc = _utc_now()
    status = "succeeded"
    error_info: tuple[str, str] | None = None
    outputs: list[dict[str, Any]] = []

    try:
        if mode == "demo":
            replay_session = replay_mod.install("replay", fixture_dir)
            print(f"[demo] replaying fixtures from {fixture_dir}")
            _check_fixture_inputs(fixture_dir, research_question, user_categories)

        # Lazy imports AFTER validation so --check-env never loads the app.
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.server import app  # noqa: PLC0415

        client = TestClient(app)

        if replay_session is not None:
            # Installed after the app imports (which may legitimately touch
            # sockets) and before any pipeline work, so a clean demo run proves
            # it needed no network at all.
            replay_mod.install_network_guard(replay_session)

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
            auto_screen=auto_screen,
            screening_info=screening_info,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced via the manifest
        status = "failed"
        error_info = (type(exc).__name__, _scrub(str(exc), api_key, endpoint))
        print(f"pipeline failed: {type(exc).__name__}", file=sys.stderr)
        if replay_session is not None and replay_session.misses:
            # FastAPI turns a cassette miss into an opaque 500, so name the real
            # cause here: stale fixtures are the likeliest way demo mode breaks.
            print(
                f"demo fixtures are stale or incomplete — {len(replay_session.misses)} "
                "cassette miss(es); re-record with scripts/record_demo.py:",
                file=sys.stderr,
            )
            for miss in replay_session.misses[:5]:
                print(f"  missing {miss}", file=sys.stderr)
    finally:
        if replay_session is not None:
            replay_session.uninstall()
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
            mode=mode,
            fixture_digest=(
                replay_session.cassettes.digest() if replay_session is not None else None
            ),
            fixture_counts=(
                replay_session.cassettes.counts() if replay_session is not None else None
            ),
            blocked_network_calls=(
                replay_session.blocked_calls if replay_session is not None else None
            ),
            cassette_misses=(replay_session.misses if replay_session is not None else None),
            screening=screening_info or None,
        )

    return 0 if status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
