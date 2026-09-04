"""Secret scanning for the committed demo fixtures.

Deliberately stdlib-only. CI runs this against ``code/demo_fixtures/`` on every
push without installing pandas, langchain, or the rest of the app, and
``capsule.replay`` re-exports it for the recorder's post-run check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that must never appear inside a committed cassette. Cassettes hold
# prompt text and response content only -- never request headers or auth values
# -- so any hit here means the recorder captured something it should not have.
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(r"\baccess_token=[A-Za-z0-9._\-]{8,}"),
    re.compile(r"\bapi[-_]?key[\"'\s:=]+[A-Za-z0-9._\-]{16,}", re.IGNORECASE),
)


def scrub_check(fixture_dir: Path) -> list[str]:
    """Report secret-shaped strings found in the fixture JSON files.

    Args:
        fixture_dir: Directory holding the JSON cassettes.

    Returns:
        Human-readable findings, one per match, each naming the file and line.
        Empty when the fixtures are clean (or the directory does not exist).
    """
    findings: list[str] = []
    if not fixture_dir.is_dir():
        return findings
    for path in sorted(fixture_dir.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.name}:{line}: matches {pattern.pattern}")
    return findings


def main(argv: list[str] | None = None) -> int:
    """Scan a fixture directory and fail if anything secret-shaped is present.

    Args:
        argv: Optional argument list; the first entry is the fixture directory
            (default ``code/demo_fixtures``).

    Returns:
        Exit code ``0`` when clean, ``1`` when findings exist.
    """
    args = sys.argv[1:] if argv is None else argv
    fixture_dir = (
        Path(args[0]) if args else Path(__file__).resolve().parent.parent / "demo_fixtures"
    )
    findings = scrub_check(fixture_dir)
    if findings:
        print(f"secret-shaped strings found in {fixture_dir}:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print(f"fixtures clean ({fixture_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
