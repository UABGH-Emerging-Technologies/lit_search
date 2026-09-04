"""Regression tests for the two failures that broke the first live recording.

Both are silent-failure bugs: the pipeline kept returning HTTP 200 while
producing an empty corpus, and only blew up two steps later with an unrelated
``KeyError: 'category'``.
"""

from __future__ import annotations

import base64
from io import BytesIO

import pandas as pd
import pytest

from capsule.screening import AUTHOR_1_COLUMN, AUTHOR_2_COLUMN, auto_screen_xlsx
from ScopingReview.BaseManager import BaseManager
from ScopingReview.Keywords.Manager import KeywordManager


def _step1_workbook(rows: int = 25) -> str:
    """Build a base64 XLSX shaped like ``BaseManager.make_initial_df`` output."""
    frame = pd.DataFrame(
        [
            {
                "title": f"Article {i}",
                "abstract": f"abstract {i}",
                "PMID": str(10000 + i),
                "keywords": "ai,surgery",
                "citation": f"Author{i} (2024)",
            }
            for i in range(rows)
        ]
    )
    frame.insert(0, AUTHOR_1_COLUMN, "No")
    frame.insert(1, AUTHOR_2_COLUMN, "No")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        frame.to_excel(writer, index=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _relevant_count(frame: pd.DataFrame) -> int:
    """Count rows the pipeline's own relevance check would keep."""
    return frame.apply(lambda row: BaseManager._check_relevance(None, row), axis=1).notna().sum()


def test_unscreened_workbook_has_zero_relevant_rows() -> None:
    """The gate that broke the recording: nothing is relevant until a human says so.

    Steps 3-5 depend on this; with zero relevant rows step 3 creates no
    ``category`` column and step 4 raises ``KeyError: 'category'``.
    """
    frame = pd.read_excel(BytesIO(base64.b64decode(_step1_workbook())))
    assert _relevant_count(frame) == 0


def test_auto_screen_opens_the_relevance_gate() -> None:
    """Auto-screening marks N articles so an unattended run can proceed."""
    screened_b64, marked, total = auto_screen_xlsx(_step1_workbook(25), limit=15)
    assert (marked, total) == (15, 25)

    frame = pd.read_excel(BytesIO(base64.b64decode(screened_b64)))
    assert _relevant_count(frame) == 15


def test_auto_screen_preserves_columns_and_clamps_to_row_count() -> None:
    """Round-tripping the workbook must not disturb the schema downstream steps read."""
    original = pd.read_excel(BytesIO(base64.b64decode(_step1_workbook(5))))
    screened_b64, marked, total = auto_screen_xlsx(_step1_workbook(5), limit=15)
    screened = pd.read_excel(BytesIO(base64.b64decode(screened_b64)))

    assert (marked, total) == (5, 5)  # clamped, not 15
    assert list(screened.columns) == list(original.columns)
    assert screened["PMID"].tolist() == original["PMID"].tolist()


def test_auto_screen_refuses_a_workbook_with_no_reviewer_column() -> None:
    """A format change must fail loudly, not yield a silently unscreened corpus."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        pd.DataFrame([{"title": "x"}]).to_excel(writer, index=False)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    with pytest.raises(KeyError, match="reviewer-column format changed"):
        auto_screen_xlsx(b64)


@pytest.mark.parametrize(
    "payload",
    [
        '{"Primary Keywords":["ai"],"Secondary Keywords":["risk"],"Exclusion Keywords":["dental"]}',
        '{"primary_keywords":["ai"],"secondary_keywords":["risk"],"exclusion_keywords":["dental"]}',
        '{"primaryKeywords":["ai"],"secondaryKeywords":["risk"],"exclusionKeywords":["dental"]}',
        'Sure!\n```json\n{"Primary Keywords":["ai"],"Secondary Keywords":["risk"],'
        '"Exclusion Keywords":["dental"]}\n```',
        '{"meta":{"n":1},"Primary Keywords":["ai"],"Secondary Keywords":["risk"],'
        '"Exclusion Keywords":["dental"]}',
    ],
    ids=["exact", "snake_case", "camelCase", "fenced", "nested-object"],
)
def test_parse_keywords_accepts_realistic_model_output(payload: str) -> None:
    """Key-name variants, fences, and nested JSON must all parse.

    The original exact-match lookup plus a non-greedy ``\\{.*?\\}`` regex turned
    every one of these into empty lists with no error, which silently disabled
    keyword filtering for the rest of the run.
    """
    primary, secondary, exclusion = KeywordManager.parse_keywords(KeywordManager, payload)
    assert primary == ["ai"]
    assert secondary == ["risk"]
    assert exclusion == ["dental"]


def test_parse_keywords_warns_when_nothing_parses(caplog: pytest.LogCaptureFixture) -> None:
    """Unparseable output still returns empty lists, but no longer silently."""
    with caplog.at_level("WARNING"):
        result = KeywordManager.parse_keywords(KeywordManager, "no json here")
    assert result == ([], [], [])
    assert "could not parse JSON" in caplog.text


def test_parse_keywords_warns_when_json_parses_but_keys_are_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valid JSON with unexpected keys is the quietest failure of all."""
    with caplog.at_level("WARNING"):
        result = KeywordManager.parse_keywords(KeywordManager, '{"topics":["ai"]}')
    assert result == ([], [], [])
    assert "no keywords at all" in caplog.text
