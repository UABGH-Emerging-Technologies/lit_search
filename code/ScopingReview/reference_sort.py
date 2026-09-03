"""
Alphabetical ordering for reference lists.

Reference sections are emitted in whatever order PubMed returned, which makes a
long list impossible to look up by author. This module provides the sort key and
DataFrame helper used by the step 4 summarize path and the standalone summary
path.

Why sorting is safe here: citations in the generated prose are author-date
("(Jin et al., 2020)"), so list position carries no meaning. It would NOT be safe
for a numbered (Vancouver) style — see config.SORT_REFERENCES for the kill
switch.

Two DataFrame shapes reach the call sites, both handled here:

  1. ``authors`` as a real list      — the standalone summary path.
  2. ``authors`` as the repr of a list after an Excel round trip — the step 4
     path reads an uploaded .xlsx, where pandas wrote and re-read the column as
     its repr string.
"""

import ast
import re
import unicodedata

_YEAR_PATTERN = re.compile(r"(\d{4})")
_PMID_PATTERN = re.compile(r"PMID:\s*(\d+)")


def normalize_sort_text(value):
    """
    Fold a name to a comparable form.

    NFKD + casefold rather than locale.strxfrm: a real locale has to be compiled
    into the image, and this container ships C/POSIX only, so strxfrm would
    silently degrade to byte ordering — the exact failure the sort is meant to
    prevent. PubMed already delivers surnames ASCII-folded ("Muller", "Jarvela"),
    so this produces the same ordering with no runtime dependency.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold()


def first_author_surname(authors):
    """
    Return the first author's surname from a PubMed ``AU`` value.

    PubMed delivers authors as "Surname Initials" ("Jin Z", "van der Mast RC").
    Multi-word surnames are kept whole, so "van der Mast" files under V — the
    default most reference managers use.

    Accepts a list, the repr of a list (an Excel round-trip artefact), or a plain
    string. Returns "" when there is no usable author, which sorts such entries
    together rather than crashing: PubMed records with only a CollectiveName have
    no ``AU`` at all.
    """
    if authors is None:
        return ""

    if isinstance(authors, (list, tuple)):
        first = authors[0] if len(authors) else ""
    else:
        text = str(authors).strip()
        if not text or text.lower() == "nan":
            return ""
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            first = text
        else:
            if isinstance(parsed, (list, tuple)):
                first = parsed[0] if len(parsed) else ""
            else:
                first = str(parsed)

    first = str(first).strip()
    if not first:
        return ""

    # "Surname Initials" -> surname. rsplit keeps multi-word surnames intact.
    parts = first.rsplit(" ", 1)
    surname = parts[0] if len(parts) == 2 else first
    return normalize_sort_text(surname)


def publication_year(value):
    """
    First four-digit run in a PubMed date, or 0 when absent.

    The date field is not a fixed format: "2020 Oct", "2018", "1999 Sep-Oct",
    "2025 Autumn" and "2020 Oct 23" all occur. Only the year is needed as a
    tiebreaker, and it is always the first four digits.
    """
    if value is None:
        return 0
    match = _YEAR_PATTERN.search(str(value))
    return int(match.group(1)) if match else 0


def sort_reference_df(df):
    """
    Return ``df`` ordered by first-author surname, then year, then title.

    Returns the input unchanged when it is empty or carries no ``authors``
    column, so the InitialSearch fallback frame passes through untouched. Never
    raises: an unsortable frame is a cosmetic problem, not a reason to fail a
    request that has already done the expensive work.
    """
    if df is None or len(df) == 0:
        return df

    try:
        import ScopingReview_config.config as config

        if not getattr(config, "SORT_REFERENCES", True):
            return df
    except Exception:  # pragma: no cover - config import is not critical
        pass

    try:
        if "authors" not in df.columns:
            return df
        surnames = df["authors"].map(first_author_surname)

        ordered = df.assign(
            _sort_surname=surnames,
            _sort_year=(
                df["date_published"].map(publication_year) if "date_published" in df.columns else 0
            ),
            _sort_title=(df["title"].map(normalize_sort_text) if "title" in df.columns else ""),
        ).sort_values(
            by=["_sort_surname", "_sort_year", "_sort_title"],
            kind="stable",
        )
        return ordered.drop(columns=["_sort_surname", "_sort_year", "_sort_title"])
    except Exception as exc:  # pragma: no cover - defensive
        print("Reference sort skipped:", exc)
        return df


def sort_citation_paragraphs(citations):
    """
    Return ``citations`` de-duplicated, then sorted alphabetically.

    Step 5 renders the References section from the draft document alone and has
    no DataFrame, so the rendered citation text is the only key available there
    — and it is also the key the reader sees. Duplicates arise because step 4
    explodes on category, so an article filed under more than one category is
    cited once per category. The first occurrence of each PMID is kept (falling
    back to the whole paragraph text when no PMID is present), then the
    survivors are ordered by their normalized text with a stable sort. Never
    raises: an unsortable list is a cosmetic problem, not a reason to fail the
    request.
    """
    if citations is None or len(citations) == 0:
        return citations

    try:
        import ScopingReview_config.config as config

        if not getattr(config, "SORT_REFERENCES", True):
            return citations
    except Exception:  # pragma: no cover - config import is not critical
        pass

    try:
        seen = set()
        deduped = []
        for citation in citations:
            pmid_match = _PMID_PATTERN.search(str(citation))
            key = pmid_match.group(1) if pmid_match else normalize_sort_text(citation)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(citation)
        return sorted(deduped, key=normalize_sort_text)
    except Exception as exc:  # pragma: no cover - defensive
        print("Citation sort skipped:", exc)
        return citations
