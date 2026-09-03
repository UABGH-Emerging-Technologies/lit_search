"""
Tests for alphabetical reference ordering.

The fixtures below are real values taken from a live /v01/standalone/summary/
run for the query "Postop delirium" — every awkward shape here occurred in that
one response, so these are not invented edge cases.
"""

import pandas as pd
import pytest

from ScopingReview.reference_sort import (
    first_author_surname,
    publication_year,
    sort_citation_paragraphs,
    sort_reference_df,
)


@pytest.mark.parametrize(
    "authors,expected",
    [
        # PubMed delivers "Surname Initials".
        (["Jin Z", "Hu J", "Ma D"], "jin"),
        # A list column that has been through an Excel round trip arrives as its repr.
        ("['Jin Z', 'Hu J', 'Ma D']", "jin"),
        # Multi-word and particle surnames stay whole, so these file under V and D
        # respectively — the default most reference managers use.
        (["van der Mast RC"], "van der mast"),
        (["de la Varga-Martinez O"], "de la varga-martinez"),
        (["Ali Hassan SM"], "ali hassan"),
        # Hyphens and apostrophes are part of the surname.
        (["Segal-Gidan F"], "segal-gidan"),
        (["O'Brien D"], "o'brien"),
        # Case is folded, so an all-caps record sorts with everything else.
        (["KROPF G"], "kropf"),
        # Records with only a CollectiveName have no AU at all; these sort together
        # rather than raising.
        ([], ""),
        (None, ""),
        ("nan", ""),
    ],
)
def test_first_author_surname(authors, expected):
    assert first_author_surname(authors) == expected


def test_suffix_sorts_where_the_citation_renders():
    """
    "Brown C 4th" yields "brown c", not "brown".

    That matches _format_authors upstream, which uses the same rsplit and renders
    the citation as "Brown C, 4th." — so the entry files under B alongside other
    Browns, which is where a reader scanning the list will look.
    """
    assert first_author_surname(["Brown C 4th"]) == "brown c"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2020 Oct", 2020),
        ("2018", 2018),
        ("1999 Sep-Oct", 1999),
        ("2025 Autumn", 2025),
        ("2020 Oct 23", 2020),
        ("No date available", 0),
        (None, 0),
    ],
)
def test_publication_year(value, expected):
    """The date field is not a fixed format; only the leading year matters."""
    assert publication_year(value) == expected


def test_sorts_by_surname_then_year():
    df = pd.DataFrame(
        [
            {"authors": ["Williams A"], "date_published": "2020", "citation": "w"},
            {"authors": ["Adams B"], "date_published": "2021", "citation": "a2"},
            {"authors": ["Adams B"], "date_published": "2019", "citation": "a1"},
            {"authors": ["Carter E"], "date_published": "2018", "citation": "c"},
        ]
    )
    assert list(sort_reference_df(df).citation) == ["a1", "a2", "c", "w"]


def test_sorts_after_an_excel_round_trip():
    """Step 4 receives an uploaded .xlsx, where `authors` is no longer a list."""
    df = pd.DataFrame(
        [
            {"authors": "['Williams A', 'Smith B']", "citation": "w"},
            {"authors": "['Adams B']", "citation": "a"},
        ]
    )
    assert list(sort_reference_df(df).citation) == ["a", "w"]


def test_surname_with_a_comma_survives_parsing():
    """Comma inside a surname is preserved; the old split(',') parsing broke it."""
    assert first_author_surname("['Mendez, Jr A', 'Hu J']") == "mendez, jr"


def test_frame_without_author_information_is_returned_unchanged():
    """
    The InitialSearch fallback frame, used when PubMed returns too few articles,
    has neither column. It must pass through rather than raise.
    """
    df = pd.DataFrame([{"citation": "Fallback et al. (2025)"}])
    assert list(sort_reference_df(df).citation) == ["Fallback et al. (2025)"]


def test_empty_frame_is_returned_unchanged():
    df = pd.DataFrame(columns=["authors", "citation"])
    assert len(sort_reference_df(df)) == 0


def test_authorless_entries_do_not_break_the_sort():
    """A record with no AU sorts to the front rather than failing the request."""
    df = pd.DataFrame(
        [
            {"authors": ["Zhang D"], "citation": "z"},
            {"authors": [], "citation": "corporate"},
            {"authors": ["Adams B"], "citation": "a"},
        ]
    )
    assert list(sort_reference_df(df).citation) == ["corporate", "a", "z"]


def test_citation_paragraphs_sort_alphabetically():
    """
    Step 5 has no DataFrame, only rendered citation paragraphs; these must come
    out in reading order even though the draft document delivered them in
    PubMed's original order.
    """
    citations = [
        "Williams, A. (2020). W. PMID: 3",
        "Adams, B. (2019). A. PMID: 1",
        "Jin, Z. (2021). J. PMID: 2",
    ]
    assert sort_citation_paragraphs(citations) == [
        "Adams, B. (2019). A. PMID: 1",
        "Jin, Z. (2021). J. PMID: 2",
        "Williams, A. (2020). W. PMID: 3",
    ]


def test_citation_paragraphs_dedupe_by_pmid():
    """
    Step 4 explodes on category, so an article filed under two categories is
    cited once per category. The duplicate must be dropped, keeping the first.
    """
    citations = [
        "Adams, B. (2019). A. PMID: 1",
        "Zhang, D. (2020). Z. PMID: 9",
        "Adams, B. (2019). A. PMID: 1",
    ]
    result = sort_citation_paragraphs(citations)
    assert len(result) == 2
    assert result == [
        "Adams, B. (2019). A. PMID: 1",
        "Zhang, D. (2020). Z. PMID: 9",
    ]


def test_citation_paragraphs_without_pmid_dedupe_on_text():
    """
    A paragraph without a PMID is de-duplicated on its normalized text, since
    that is the only key available - and the only key the reader sees.
    """
    citations = [
        "No PMID here, Adams",
        "No PMID here, Adams",
        "No PMID here, Baker",
    ]
    assert len(sort_citation_paragraphs(citations)) == 2


def test_citation_paragraphs_empty_input_returned_unchanged():
    """An empty list and None must pass through untouched, matching the frame."""
    assert sort_citation_paragraphs([]) == []
    assert sort_citation_paragraphs(None) is None
