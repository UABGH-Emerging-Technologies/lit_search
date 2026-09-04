"""Tests for the capsule record/replay layer.

These tests verify the three external seams (LLM, PubMed search/details/fulltext)
can be recorded offline and replayed without network access.

Note: ``code/tests/fastapi_tests/conftest.py`` lives in a sibling directory and
does NOT apply here, so no autouse mocks are active. Each test sets up and tears
down its own patches.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from aiweb_common.resource.PubMedInterface import PubMedInterface
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    get_buffer_string,
)
from langchain_core.prompt_values import ChatPromptValue

from capsule.replay import (
    CASSETTE_FILES,
    Cassettes,
    NetworkBlocked,
    _build_replay_chat_model,
    _df_to_records,
    _records_to_df,
    _sha,
    canonical_prompt_text,
    install,
    install_network_guard,
    scrub_check,
)


# ---------------------------------------------------------------------------
# Test 1
# ---------------------------------------------------------------------------
def test_canonical_key_agrees_across_record_and_replay() -> None:
    """A ``ChatPromptValue`` and its message list must hash to the same key.

    Recording observes a ``ChatPromptValue`` (from ``PromptAssembler.assemble``),
    while replay observes ``list[BaseMessage]`` (from
    ``BaseChatModel._convert_input``).  Both normalize to the same buffer string
    so the cassette lookup succeeds regardless of which side of the conversion
    they observe.
    """
    msgs: list[BaseMessage] = [SystemMessage(content="sys"), HumanMessage(content="hi")]
    pv = ChatPromptValue(messages=msgs)

    assert _sha(canonical_prompt_text(pv)) == _sha(canonical_prompt_text(msgs))


# ---------------------------------------------------------------------------
# Test 2
# ---------------------------------------------------------------------------
def test_dataframe_roundtrip_preserves_pmid_join() -> None:
    """PMID dtype, list cells, and merge correctness survive JSON round-trip.

    ``Categorize`` merges ``reduced_df`` and ``full_text_df`` on PMID.  A dtype
    regression (string PMID inferred as ``int64``) makes the merge silently
    return zero rows instead of raising.  This test guards that path
    end-to-end through the real ``_df_to_records`` / ``_records_to_df`` helpers
    and ``Cassettes.save`` (which writes with ``sort_keys=True`` and
    ``allow_nan=False``).
    """
    details = pd.DataFrame(
        [
            {
                "date_published": "2020",
                "title": "Study One",
                "keywords": ["headache", "surgery"],
                "abstract": "Abstract text one",
                "pmid": "12345",
                "authors": ["Author A"],
                "journal": "Journal A",
                "citation": "Citation A",
            },
            {
                "date_published": "2021",
                "title": "Study Two",
                "keywords": [],
                "abstract": None,
                "pmid": "67890",
                "authors": [],
                "journal": "Journal B",
                "citation": "Citation B",
            },
        ]
    )

    fulltext = pd.DataFrame(
        [
            {
                "PMID": "12345",
                "URL": "http://example.com/1",
                "Downloaded": True,
                "Text": "Full text one",
            },
            {
                "PMID": "67890",
                "URL": None,
                "Downloaded": False,
                "Text": None,
            },
        ]
    )

    # --- Round-trip *details* ---
    details_payload = _df_to_records(details)
    details_json = json.dumps(details_payload, allow_nan=False)
    details_rt = _records_to_df(json.loads(details_json), ("pmid",))

    # --- Round-trip *fulltext* ---
    fulltext_payload = _df_to_records(fulltext)
    fulltext_json = json.dumps(fulltext_payload, allow_nan=False)
    fulltext_rt = _records_to_df(json.loads(fulltext_json), ("PMID",))

    # json.dumps with allow_nan=False must not raise — fixtures must be
    # strict valid JSON.  (If _jsonable missed a NaN it would blow up above.)

    # pmid / PMID columns come back as strings, not integers
    assert pd.api.types.is_string_dtype(details_rt["pmid"])
    assert pd.api.types.is_string_dtype(fulltext_rt["PMID"])
    assert not pd.api.types.is_integer_dtype(details_rt["pmid"])
    assert not pd.api.types.is_integer_dtype(fulltext_rt["PMID"])

    # list cells survive as lists
    assert isinstance(details_rt["keywords"].iloc[0], list)
    assert isinstance(details_rt["authors"].iloc[0], list)
    assert isinstance(details_rt["keywords"].iloc[1], list)  # empty list survives
    assert isinstance(details_rt["authors"].iloc[1], list)

    # The merge is the point: a dtype mismatch would silently return 0 rows
    merged = pd.merge(
        details_rt.rename(columns={"pmid": "PMID"}),
        fulltext_rt,
        on="PMID",
        how="inner",
    )
    assert len(merged) == 2


# ---------------------------------------------------------------------------
# Test 3
# ---------------------------------------------------------------------------
def test_record_then_replay_roundtrip_for_pubmed_seams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Recording PubMed seams then replaying yields identical results.

    The three ``PubMedInterface`` methods are monkeypatched with fakes *before*
    ``install('record')`` is called, so the recorder wraps the fakes rather than
    touching the network.  After saving and uninstalling, ``install('replay')``
    serves the recorded values back.  Every session is cleaned up with
    ``try/finally`` so patched classes never leak between tests.
    """

    def fake_search(self: Any, query: str) -> list[str]:
        return ["12345", "67890"]

    def fake_details(self: Any, pubmed_ids: Any) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "date_published": "2020",
                    "title": "Study One",
                    "keywords": ["headache", "surgery"],
                    "abstract": None,
                    "pmid": "12345",
                    "authors": ["Author A"],
                    "journal": "Journal A",
                    "citation": "Citation A",
                },
                {
                    "date_published": "2021",
                    "title": "Study Two",
                    "keywords": [],
                    "abstract": "Abstract two",
                    "pmid": "67890",
                    "authors": [],
                    "journal": "Journal B",
                    "citation": "Citation B",
                },
            ]
        )

    def fake_full_text(
        self: Any,
        pmids: Any,
        access_token: Any = None,
        library_number: Any = None,
    ) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "PMID": "12345",
                    "URL": "http://example.com/1",
                    "Downloaded": True,
                    "Text": "Full text one",
                },
                {
                    "PMID": "67890",
                    "URL": None,
                    "Downloaded": False,
                    "Text": None,
                },
            ]
        )

    # Monkeypatch *before* install('record') so the recorder wraps the fakes.
    monkeypatch.setattr(PubMedInterface, "search_pubmed_articles", fake_search)
    monkeypatch.setattr(PubMedInterface, "fetch_article_details", fake_details)
    monkeypatch.setattr(PubMedInterface, "fetch_full_text", fake_full_text)

    # --- Record phase -------------------------------------------------------
    record_session = install("record", tmp_path)
    try:
        inst = PubMedInterface()
        recorded_search = inst.search_pubmed_articles("some query")
        recorded_details = inst.fetch_article_details(["12345", "67890"])
        recorded_fulltext = inst.fetch_full_text(["12345", "67890"], "tok", "731")
        record_session.save()
    finally:
        record_session.uninstall()

    # --- Replay phase -------------------------------------------------------
    replay_session = install("replay", tmp_path)
    try:
        inst2 = PubMedInterface()
        replayed_search = inst2.search_pubmed_articles("some query")
        replayed_details = inst2.fetch_article_details(["12345", "67890"])
        replayed_fulltext = inst2.fetch_full_text(["12345", "67890"], "tok", "731")

        # Search returns a list of PMIDs — exact equality.
        assert recorded_search == replayed_search

        # DataFrames must be equal (column order is preserved by the payload).
        pd.testing.assert_frame_equal(replayed_details, recorded_details, check_dtype=False)
        pd.testing.assert_frame_equal(replayed_fulltext, recorded_fulltext, check_dtype=False)

        # PMID columns must be string dtype, not integer.
        assert pd.api.types.is_string_dtype(replayed_details["pmid"])
        assert pd.api.types.is_string_dtype(replayed_fulltext["PMID"])
    finally:
        replay_session.uninstall()


# ---------------------------------------------------------------------------
# Test 4
# ---------------------------------------------------------------------------
def test_replay_chat_model_serves_recorded_content_and_populates_callback() -> None:
    """The replay model serves recorded content and fires LangChain callbacks.

    Because ``_ReplayChatModel`` subclasses ``BaseChatModel``, calling
    ``invoke`` inside a ``get_openai_callback`` context drives the full callback
    stack.  No real API is called, so ``total_cost`` must be ``0.0``.
    """
    msgs: list[BaseMessage] = [SystemMessage(content="sys"), HumanMessage(content="hi")]
    pv = ChatPromptValue(messages=msgs)
    key = _sha(get_buffer_string(msgs))

    replay_model_cls = _build_replay_chat_model()
    model = replay_model_cls(cassette={key: "RECORDED"})

    assert model.invoke(pv).content == "RECORDED"

    with get_openai_callback() as cb:
        result = model.invoke(pv)
        assert result.content == "RECORDED"
        assert cb.total_cost == 0.0


# ---------------------------------------------------------------------------
# Test 5
# ---------------------------------------------------------------------------
def test_replay_cassette_miss_raises_keyerror() -> None:
    """A prompt absent from the cassette must raise ``KeyError``, not guess.

    Returning a wrong-but-plausible answer would be far more damaging than a
    loud failure, so the replay model raises ``KeyError`` whose message points
    at the re-recording script.
    """
    msgs: list[BaseMessage] = [SystemMessage(content="sys"), HumanMessage(content="hi")]
    pv = ChatPromptValue(messages=msgs)

    replay_model_cls = _build_replay_chat_model()
    model = replay_model_cls(cassette={})  # empty — guaranteed miss

    with pytest.raises(KeyError, match="re-record"):
        model.invoke(pv)


# ---------------------------------------------------------------------------
# Test 6
# ---------------------------------------------------------------------------
def test_load_fails_clearly_when_fixtures_missing(tmp_path: Path) -> None:
    """``Cassettes.load`` on an empty dir raises ``FileNotFoundError``.

    The message must name every missing cassette file and point to the
    recording script so the user knows how to fix the problem.
    """
    with pytest.raises(FileNotFoundError) as exc_info:
        Cassettes.load(tmp_path)

    message = str(exc_info.value)
    for name in CASSETTE_FILES:
        assert name in message, f"{name} should be named in the error message"
    assert "record_demo.py" in message


# ---------------------------------------------------------------------------
# Test 7
# ---------------------------------------------------------------------------
def test_network_guard_blocks_sockets_and_dns_and_counts(
    tmp_path: Path,
) -> None:
    """The network guard blocks DNS/connection calls and counts each attempt.

    ``NetworkBlocked`` subclasses ``OSError`` so callers that already degrade
    gracefully on socket failure (``app.v01.net_validators``) keep working,
    while everything else fails loudly.  Three blocking operations must be
    counted, and after ``uninstall`` the socket functions must be restored.
    """
    # Create valid empty cassettes so install('replay') can load them.
    Cassettes(fixture_dir=tmp_path).save()

    session = install("replay", tmp_path)
    install_network_guard(session)
    try:
        # DNS resolution (used by net_validators) is blocked.
        with pytest.raises(NetworkBlocked):
            socket.getaddrinfo("example.com", 80)

        # Outbound connection is blocked.
        with pytest.raises(NetworkBlocked):
            socket.create_connection(("example.com", 80))

        # Hostname lookup is blocked.
        with pytest.raises(NetworkBlocked):
            socket.gethostbyname("example.com")

        # NetworkBlocked is an OSError subclass.
        assert issubclass(NetworkBlocked, OSError)

        # Exactly three blocking attempts were counted.
        assert session.blocked_calls == 3
    finally:
        session.uninstall()

    # After uninstall, socket functions are restored to their originals.
    socket.getaddrinfo("127.0.0.1", 80)
    sock = socket.socket()
    sock.close()


# ---------------------------------------------------------------------------
# Test 8
# ---------------------------------------------------------------------------
def test_scrub_check_flags_secret_shaped_strings(tmp_path: Path) -> None:
    """``scrub_check`` flags secret-shaped strings in cassette JSON files.

    A cassette containing an ``sk-``-style key triggers a finding that names
    the file; a clean directory returns an empty list.
    """
    # Deliberate fake key for the scrub test.  pragma: allowlist secret
    secret = "sk-abcdefghijklmnopqrstuvwxyz012345"  # pragma: allowlist secret
    cassette = tmp_path / "llm.json"
    cassette.write_text(
        json.dumps({"response": secret}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    findings = scrub_check(tmp_path)
    assert len(findings) > 0, "expected at least one secret-shaped finding"
    assert "llm.json" in findings[0], "finding should name the file"

    # A clean directory (no JSON files) returns no findings.
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    assert scrub_check(clean_dir) == []
