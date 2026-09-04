#!/usr/bin/env python3
"""Record one real pipeline run into the offline demo fixtures.

Run this once, locally, with real credentials. It executes exactly the same code
path the capsule uses (``capsule_driver._run_pipeline`` through ``TestClient``)
with recording doubles wrapped around the three external seams, then writes the
captured interactions to ``code/demo_fixtures/``.

    cd code && python scripts/record_demo.py

Afterwards the capsule replays those fixtures with no credentials and no
network. Re-record whenever a prompt template, a workflow's call sequence, or
the demo research question changes -- replay keys on exact prompt text, so a
changed prompt is a cassette miss, by design.

Security contract:
    Only prompt text and response content are captured. Request headers,
    ``Authorization`` values, and API keys are never written. The run ends with
    a scrub pass that fails the recording if anything secret-shaped slipped in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capsule import replay as replay_mod  # noqa: E402
from scripts import capsule_driver as driver  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Record a full pipeline run into the demo fixture directory.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code ``0`` on success, ``1`` on missing credentials, a pipeline
        failure, or a failed scrub check.
    """
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Fixture output directory (default: code/demo_fixtures).",
    )
    parser.add_argument(
        "--auto-screen",
        type=int,
        default=driver.DEFAULT_SCREEN_LIMIT,
        help=(
            "Mark this many step-1 articles reviewer-relevant so the unattended run "
            "can pass the human screening gate (default: %(default)s). 0 disables, "
            "which will fail at step 3 unless the corpus already carries reviewer marks."
        ),
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore existing fixtures and re-request every call (costs money).",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="Where to write the run's artifacts (default: code/results/record).",
    )
    args = parser.parse_args(argv)

    fixture_dir = args.out or driver.resolve_fixture_dir(repo_root)
    results_dir = args.results or (repo_root / "results" / "record")
    results_dir.mkdir(parents=True, exist_ok=True)

    driver.mirror_upper_to_lower()
    missing = driver.missing_required_names()
    if missing:
        print("recording needs real credentials; missing:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1

    data_dir = driver.resolve_data_dir(repo_root)
    research_question = driver.resolve_research_question(data_dir)
    # Same default the capsule replays with -- see DEFAULT_DEMO_CATEGORIES.
    user_categories = driver.env_any("USER_DEFINED_CATEGORIES") or driver.DEFAULT_DEMO_CATEGORIES
    api_key, endpoint, model = driver.read_credentials()
    frozen_b64 = driver.load_frozen_step1(data_dir)

    session = replay_mod.install("record", fixture_dir, resume=not args.fresh)
    if session.cassettes.counts()["llm"]:
        print(f"[record] resuming — reusing {session.cassettes.counts()} already recorded")
    outputs: list[dict[str, Any]] = []
    screening_info: dict[str, Any] = {}
    failed = False
    try:
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.server import app  # noqa: PLC0415

        print(f"[record] research question: {research_question}")
        driver._run_pipeline(
            TestClient(app),
            results_dir,
            research_question,
            user_categories,
            api_key,
            endpoint,
            model,
            frozen_b64,
            outputs,
            auto_screen=args.auto_screen,
            screening_info=screening_info,
        )
    except Exception as exc:  # noqa: BLE001 - reported without leaking the key
        failed = True
        print(
            f"recording failed: {type(exc).__name__}: "
            f"{driver._scrub(str(exc), api_key, endpoint)}",
            file=sys.stderr,
        )
    finally:
        session.uninstall()
        # Save unconditionally. A failed run has already paid for every call it
        # made; discarding them would mean paying again on the next attempt.
        if not failed:
            # Only safe on a complete run: every entry the pipeline needs was used.
            pruned = session.prune_unused()
            if any(pruned.values()):
                print(f"[record] pruned unused entries: {pruned}")
        session.save()
        print(
            f"[record] {session.live_calls} live call(s), "
            f"{session.reused_calls} reused; fixtures saved to {fixture_dir}"
        )

    counts = session.cassettes.counts()
    (fixture_dir / replay_mod.FIXTURE_MANIFEST).write_text(
        json.dumps(
            {
                "recorded_utc": driver._utc_now(),
                "research_question": research_question,
                "user_defined_categories": user_categories,
                "counts": counts,
                "complete": not failed,
                "screening": screening_info or None,
                "digest": session.cassettes.digest(),
                "git_commit": driver._git_commit(repo_root),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    findings = replay_mod.scrub_check(fixture_dir)
    if findings:
        print("SCRUB FAILED - fixtures contain secret-shaped strings:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print("Do NOT commit these fixtures.", file=sys.stderr)
        return 1

    for seam, count in counts.items():
        print(f"  {seam}: {count}")
    if failed:
        print(
            "[record] PARTIAL — the pipeline did not finish. The calls above are "
            "saved; fix the failure and re-run to resume from here.",
            file=sys.stderr,
        )
        return 1
    print("[record] scrub check passed; review the fixtures before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
