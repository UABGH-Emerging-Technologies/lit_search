"""Synthetic relevance screening for unattended capsule runs.

The scoping-review pipeline has a human-in-the-loop gate between step 1 and
step 2. ``BaseManager.make_initial_df`` inserts two columns --
``Author 1: Relevant Article? (Yes/No)`` and ``Author 2: ...`` -- defaulted to
``"No"``. A researcher downloads the step-1 spreadsheet, marks the articles
worth keeping, and re-uploads it. ``BaseManager._check_relevance`` then treats a
``Yes`` from either author as relevant.

The capsule driver runs all six steps unattended, so nobody ever marks anything.
Every row stays ``No``, ``get_relevant_rows()`` returns an empty frame, step 3's
categorization loop iterates zero times, the ``category`` column is never
created, and step 4 dies with ``KeyError: 'category'``.

This module marks the first N articles ``Yes`` so the pipeline can run end to
end. **These are not real screening decisions.** Callers must surface that in
the run manifest and the results directory -- see ``NOTICE``.
"""

from __future__ import annotations

import base64
from io import BytesIO

import pandas as pd

# Column written by BaseManager.make_initial_df for the first reviewer.
AUTHOR_1_COLUMN = "Author 1: Relevant Article? (Yes/No)"
AUTHOR_2_COLUMN = "Author 2: Relevant Article? (Yes/No)"

# Default number of articles to mark. Large enough to give step 4 several
# categories to summarize, small enough to keep a recording affordable.
DEFAULT_SCREEN_LIMIT = 15

NOTICE = (
    "SYNTHETIC SCREENING: this run marked the first {marked} of {total} articles as "
    "relevant automatically. A real scoping review requires two human reviewers to "
    "screen every article; these outputs demonstrate the pipeline mechanics only and "
    "must not be read as a screening result."
)


def auto_screen_xlsx(
    xlsx_b64: str,
    limit: int = DEFAULT_SCREEN_LIMIT,
    column: str = AUTHOR_1_COLUMN,
) -> tuple[str, int, int]:
    """Mark the first ``limit`` articles as reviewer-relevant in a step-1 workbook.

    Args:
        xlsx_b64: Base64-encoded step-1 XLSX as returned by the API.
        limit: Maximum number of rows to mark ``Yes``.
        column: Reviewer column to write into.

    Returns:
        A ``(xlsx_b64, marked, total)`` tuple: the re-encoded workbook, how many
        rows were marked, and how many rows the workbook held.

    Raises:
        KeyError: If the workbook has no reviewer column to write into, which
            means the upstream format changed and the caller should stop rather
            than silently produce an unscreened corpus.
    """
    frame = pd.read_excel(BytesIO(base64.b64decode(xlsx_b64)))
    if column not in frame.columns:
        raise KeyError(
            f"step-1 workbook has no {column!r} column (found {list(frame.columns)!r}); "
            "the reviewer-column format changed, so auto-screening cannot proceed"
        )

    total = len(frame)
    marked = min(limit, total)
    if marked:
        frame.loc[frame.index[:marked], column] = "Yes"

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        frame.to_excel(writer, index=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii"), marked, total
