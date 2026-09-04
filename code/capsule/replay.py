"""Record and replay the scoping pipeline's external seams.

The Code Ocean capsule must run for anyone, with no credentials and no network.
This module makes that possible by recording one real end-to-end run into JSON
fixtures and replaying them offline afterwards.

The pipeline reaches the network in exactly three places:

1. ``llm_interface.invoke()`` -- every workflow builds
   ``SingleResponseHandler(self.llm_interface)`` and calls ``generate_response``,
   landing in ``aiweb_common.generate.QueryInterface.generate_langchain_response``.
2. ``PubMedInterface.search_pubmed_articles`` / ``fetch_article_details`` (Entrez).
3. ``PubMedInterface.fetch_full_text`` (PMC + LibKey).

``install(mode, fixture_dir)`` doubles all three. ``record`` wraps the real
implementations and captures their results; ``replay`` serves the captured
results and never touches the network.

Security contract:
    Cassettes hold prompt text and response content only. Request headers,
    ``Authorization`` values, and API keys are never captured. ``scrub_check``
    enforces that before fixtures are committed.
"""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompt_values import PromptValue

from capsule.scrub import scrub_check  # re-exported for the recorder  # noqa: F401

# Cassette filenames within the fixture directory.
LLM_CASSETTE = "llm.json"
SEARCH_CASSETTE = "pubmed_search.json"
DETAILS_CASSETTE = "pubmed_details.json"
FULLTEXT_CASSETTE = "pubmed_fulltext.json"
FIXTURE_MANIFEST = "fixtures.json"

CASSETTE_FILES: tuple[str, ...] = (
    LLM_CASSETTE,
    SEARCH_CASSETTE,
    DETAILS_CASSETTE,
    FULLTEXT_CASSETTE,
)

# Endpoint advertised to the API in demo mode. ``.invalid`` is reserved by
# RFC 2606 and can never resolve, so a leaked live call fails loudly.
DEMO_ENDPOINT = "https://demo.invalid/v1"
DEMO_ENDPOINT_HOST = "demo.invalid"
DEMO_MODEL = "demo-replay"

# Join keys that must survive serialization as strings. ``Categorize`` merges
# ``reduced_df`` and ``full_text_df`` on PMID; a dtype mismatch there does not
# raise, it silently yields zero rows.
_JOIN_KEY_COLUMNS: dict[str, tuple[str, ...]] = {
    DETAILS_CASSETTE: ("pmid",),
    FULLTEXT_CASSETTE: ("PMID",),
}


class NetworkBlocked(OSError):
    """Raised when demo mode intercepts an attempted network call.

    Subclasses ``OSError`` deliberately: callers that already degrade
    gracefully on socket failure (``app.v01.net_validators``) keep working,
    while everything else fails loudly.
    """


def _sha(text: str) -> str:
    """Return the hex SHA-256 of ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_prompt_text(value: Any) -> str:
    """Render any LangChain chat input to the one canonical string used for keying.

    ``PromptAssembler.assemble_prompt`` returns a ``ChatPromptValue``, while
    ``BaseChatModel._convert_input`` hands ``_generate`` a ``list[BaseMessage]``.
    Both normalize to the same buffer string, so recording and replay agree on
    the cassette key regardless of which side of the conversion they observe.

    Args:
        value: A ``PromptValue``, a string, a ``BaseMessage``, or an iterable of
            messages.

    Returns:
        The canonical ``"System: ...\\nHuman: ..."`` rendering.
    """
    if isinstance(value, PromptValue):
        messages: list[BaseMessage] = value.to_messages()
    elif isinstance(value, str):
        messages = [HumanMessage(content=value)]
    elif isinstance(value, BaseMessage):
        messages = [value]
    else:
        messages = list(value)
    return get_buffer_string(messages)


def _pmid_key(pmids: Iterable[Any]) -> str:
    """Key a PubMed call by its input IDs in call order.

    Order is preserved deliberately: the pipeline zips results back against the
    input sequence, so a sorted key would let a reordered call silently match.

    Args:
        pmids: PubMed IDs, possibly a pandas Series.

    Returns:
        A hex digest over the ordered, stringified IDs.
    """
    return _sha(json.dumps([str(pmid) for pmid in pmids], separators=(",", ":")))


def _jsonable(value: Any) -> Any:
    """Coerce one DataFrame cell to a strictly JSON-serializable value.

    Two things need handling. Missing values arrive as ``NaN``/``NaT``, and
    ``json.dumps`` would emit a bare ``NaN`` token -- accepted by Python's own
    loader but not valid JSON, which would make the fixtures unportable. And
    numpy scalars (``np.bool_``, ``np.int64``) are not serializable at all.

    Args:
        value: A raw cell value.

    Returns:
        ``None`` for missing values, a Python scalar for numpy types, the
        element-wise cleaned list for sequence cells, else ``value`` unchanged.
    """
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item") and getattr(value, "ndim", None) == 0:
        value = value.item()
    if value is None:
        return None
    if isinstance(value, (str, bytes, bool, int)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _df_to_records(frame: pd.DataFrame | None) -> dict[str, Any] | None:
    """Serialize a DataFrame to a strictly JSON-safe payload, or ``None`` passthrough.

    Column order is stored explicitly rather than being implied by key order in
    the record dicts. Cassettes are written with ``sort_keys=True`` so they diff
    cleanly, and that sorting is recursive -- without an explicit column list the
    replayed frame would come back alphabetized, silently changing the column
    layout of the generated XLSX relative to a live run.

    Args:
        frame: The DataFrame to serialize, or ``None``.

    Returns:
        A ``{"columns": [...], "records": [...]}`` payload, or ``None``.
    """
    if frame is None:
        return None
    return {
        "columns": [str(column) for column in frame.columns],
        "records": [
            {key: _jsonable(value) for key, value in record.items()}
            for record in frame.to_dict(orient="records")
        ],
    }


def _records_to_df(
    payload: dict[str, Any] | None, join_keys: tuple[str, ...]
) -> pd.DataFrame | None:
    """Rebuild a DataFrame from a cassette payload, restoring order and dtypes.

    ``pd.DataFrame(records)`` is used rather than ``pd.read_json`` because the
    latter infers numeric-looking string columns as ``int64`` -- which would
    break the PMID merge in ``Categorize`` silently rather than loudly.

    Args:
        payload: A ``{"columns": [...], "records": [...]}`` mapping, or ``None``.
        join_keys: Columns to coerce back to ``str``.

    Returns:
        The rebuilt DataFrame, or ``None`` when ``payload`` is ``None``.
    """
    if payload is None:
        return None
    records = payload["records"]
    columns = payload["columns"]
    frame = pd.DataFrame(records, columns=columns) if records else pd.DataFrame(columns=columns)
    for column in join_keys:
        if column in frame.columns:
            frame[column] = frame[column].astype(str)
    return frame


@dataclass
class Cassettes:
    """In-memory cassette store backed by one JSON file per seam."""

    fixture_dir: Path
    llm: dict[str, Any] = field(default_factory=dict)
    search: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    fulltext: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, fixture_dir: Path) -> "Cassettes":
        """Read every cassette file from ``fixture_dir``.

        Args:
            fixture_dir: Directory holding the JSON cassettes.

        Returns:
            A populated ``Cassettes`` instance.

        Raises:
            FileNotFoundError: If any cassette file is missing.
        """
        missing = [name for name in CASSETTE_FILES if not (fixture_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(
                f"demo fixtures incomplete in {fixture_dir}: missing {', '.join(missing)}. "
                "Record them with scripts/record_demo.py."
            )

        def read(name: str) -> Any:
            return json.loads((fixture_dir / name).read_text(encoding="utf-8"))

        return cls(
            fixture_dir=fixture_dir,
            llm=read(LLM_CASSETTE),
            search=read(SEARCH_CASSETTE),
            details=read(DETAILS_CASSETTE),
            fulltext=read(FULLTEXT_CASSETTE),
        )

    @classmethod
    def load_partial(cls, fixture_dir: Path) -> "Cassettes":
        """Load whatever cassettes exist, tolerating missing or partial files.

        Used to resume a recording. A run that dies mid-pipeline has already
        paid for every call it made, so those responses are reused rather than
        re-requested on the next attempt.

        Args:
            fixture_dir: Directory that may hold some or none of the cassettes.

        Returns:
            A ``Cassettes`` instance populated from whatever was present.
        """

        def read(name: str) -> dict[str, Any]:
            path = fixture_dir / name
            if not path.is_file():
                return {}
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}

        return cls(
            fixture_dir=fixture_dir,
            llm=read(LLM_CASSETTE),
            search=read(SEARCH_CASSETTE),
            details=read(DETAILS_CASSETTE),
            fulltext=read(FULLTEXT_CASSETTE),
        )

    def save(self) -> None:
        """Write every cassette to ``fixture_dir`` as sorted, indented JSON."""
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in (
            (LLM_CASSETTE, self.llm),
            (SEARCH_CASSETTE, self.search),
            (DETAILS_CASSETTE, self.details),
            (FULLTEXT_CASSETTE, self.fulltext),
        ):
            # allow_nan=False so a stray NaN fails here rather than producing a
            # cassette that only Python can read back.
            (self.fixture_dir / name).write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
                + "\n",
                encoding="utf-8",
            )

    def digest(self) -> str:
        """Return a stable digest over every cassette key, for the run manifest."""
        keys = sorted(list(self.llm) + list(self.search) + list(self.details) + list(self.fulltext))
        return _sha("\n".join(keys))

    def counts(self) -> dict[str, int]:
        """Return the number of recorded interactions per seam."""
        return {
            "llm": len(self.llm),
            "pubmed_search": len(self.search),
            "pubmed_details": len(self.details),
            "pubmed_fulltext": len(self.fulltext),
        }


def _build_replay_chat_model(on_miss: Callable[[str], None] | None = None) -> type:
    """Construct the replay chat model class.

    The double must be a genuine ``BaseChatModel``. ``QueryInterface.
    generate_langchain_response`` wraps every call in ``get_openai_callback()``,
    which is populated through LangChain's callback manager -- machinery that
    only runs inside ``BaseChatModel.invoke``. A duck-typed object with an
    ``.invoke`` method would leave ``response_meta`` unpopulated and silently
    zero out cost accounting.

    Args:
        on_miss: Called with a short description when a lookup fails, so the
            driver can report the real cause behind FastAPI's opaque 500.

    Returns:
        A ``BaseChatModel`` subclass performing keyed cassette lookup.
    """
    from langchain_core.language_models.chat_models import (  # noqa: PLC0415
        BaseChatModel,
    )

    class _ReplayChatModel(BaseChatModel):
        """Serve recorded completions keyed by canonical prompt text."""

        cassette: dict[str, Any] = {}

        @property
        def _llm_type(self) -> str:
            return "lit-search-replay"

        def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> ChatResult:
            key = _sha(get_buffer_string(messages))
            if key not in self.cassette:
                if on_miss is not None:
                    on_miss(f"LLM prompt (hash {key})")
                raise KeyError(
                    "replay cassette miss: no recorded response for this prompt "
                    f"(hash {key}). The prompt or its inputs changed since the "
                    "fixtures were recorded; re-record with scripts/record_demo.py.\n"
                    f"--- prompt ---\n{get_buffer_string(messages)}"
                )
            content = self.cassette[key]
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    return _ReplayChatModel


@dataclass
class ReplaySession:
    """Handle returned by :func:`install`, holding the cassettes and undo hooks."""

    mode: str
    cassettes: Cassettes
    _undo: list[Callable[[], None]] = field(default_factory=list)
    blocked_calls: int = 0
    reused_calls: int = 0
    live_calls: int = 0
    used: dict[str, set[str]] = field(
        default_factory=lambda: {"llm": set(), "search": set(), "details": set(), "fulltext": set()}
    )
    misses: list[str] = field(default_factory=list)

    def prune_unused(self) -> dict[str, int]:
        """Drop recorded entries this run never touched.

        Fixtures accumulate dead weight across resumed recordings: a prompt that
        changes leaves its old response behind forever, and an abandoned PubMed
        query can leave megabytes of article metadata nothing will ever read.
        Call this only after a *complete* run, where every entry the pipeline
        needs has necessarily been used.

        Returns:
            Per-seam count of removed entries.
        """
        removed: dict[str, int] = {}
        for seam in ("llm", "search", "details", "fulltext"):
            store = getattr(self.cassettes, seam)
            stale = [key for key in store if key not in self.used[seam]]
            for key in stale:
                del store[key]
            removed[seam] = len(stale)
        return removed

    def record_miss(self, description: str) -> None:
        """Note a cassette miss so the driver can report the real cause.

        FastAPI turns the raised ``KeyError`` into an opaque HTTP 500, which
        hides the one failure users are most likely to hit: fixtures that went
        stale after a prompt change.

        Args:
            description: Short description of what could not be found.
        """
        self.misses.append(description)

    def uninstall(self) -> None:
        """Restore every patched attribute, most recent first."""
        while self._undo:
            self._undo.pop()()

    def save(self) -> None:
        """Persist the cassettes (recording mode)."""
        self.cassettes.save()


def _patch(session: ReplaySession, owner: Any, name: str, replacement: Any) -> None:
    """Set ``owner.name`` to ``replacement`` and register the undo."""
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    session._undo.append(lambda: setattr(owner, name, original))


def install(mode: str, fixture_dir: Path, resume: bool = True) -> ReplaySession:
    """Double the pipeline's three external seams.

    Args:
        mode: ``"record"`` to wrap the real implementations and capture their
            results, or ``"replay"`` to serve captured results offline.
        fixture_dir: Directory holding (or to hold) the JSON cassettes.
        resume: Recording only. When true, reuse an already-recorded response
            instead of paying for the call again. Keys are prompt hashes, so a
            changed prompt still misses and goes live.

    Returns:
        A :class:`ReplaySession`. Call ``save()`` after a recording run.

    Raises:
        ValueError: If ``mode`` is neither ``"record"`` nor ``"replay"``.
        FileNotFoundError: In replay mode, if any cassette is missing.
    """
    if mode not in ("record", "replay"):
        raise ValueError(f"mode must be 'record' or 'replay', got {mode!r}")

    from aiweb_common.generate.QueryInterface import (  # noqa: PLC0415
        QueryInterface,
    )
    from aiweb_common.resource.PubMedInterface import (  # noqa: PLC0415
        PubMedInterface,
    )
    from aiweb_common.WorkflowHandler import WorkflowHandler  # noqa: PLC0415

    if mode == "replay":
        cassettes = Cassettes.load(fixture_dir)
    elif resume:
        cassettes = Cassettes.load_partial(fixture_dir)
    else:
        cassettes = Cassettes(fixture_dir=fixture_dir)
    session = ReplaySession(mode=mode, cassettes=cassettes)

    if mode == "record":
        _install_recorders(session, QueryInterface, PubMedInterface, resume)
    else:
        _install_replayers(session, WorkflowHandler, PubMedInterface)

    return session


@dataclass
class _ReusedMeta:
    """Stand-in for ``get_openai_callback``'s meta on a reused recording.

    ``WorkflowHandler._update_total_cost`` reads only ``total_cost``. A reused
    call costs nothing, so zero is the honest value.
    """

    total_cost: float = 0.0


def _install_recorders(
    session: ReplaySession, query_interface: type, pubmed_interface: type, resume: bool = True
) -> None:
    """Wrap the real seams so their results land in the cassettes.

    With ``resume``, an already-recorded response short-circuits the live call.
    A recording that dies mid-pipeline has already paid for everything it got
    through, and each attempt costs hundreds of LLM calls, so the next attempt
    resumes rather than re-spending.
    """
    cassettes = session.cassettes

    original_generate = query_interface.generate_langchain_response

    def recording_generate(self: Any, assembled_prompt: Any) -> Any:
        key = _sha(canonical_prompt_text(assembled_prompt))
        session.used["llm"].add(key)
        if resume and key in cassettes.llm:
            session.reused_calls += 1
            return AIMessage(content=cassettes.llm[key]), _ReusedMeta()
        response, meta = original_generate(self, assembled_prompt)
        session.live_calls += 1
        cassettes.llm[key] = response.content
        return response, meta

    _patch(session, query_interface, "generate_langchain_response", recording_generate)

    original_search = pubmed_interface.search_pubmed_articles

    def recording_search(self: Any, query: str) -> Any:
        key = _sha(query)
        session.used["search"].add(key)
        if resume and key in cassettes.search:
            session.reused_calls += 1
            return cassettes.search[key]
        result = original_search(self, query)
        session.live_calls += 1
        cassettes.search[key] = list(result) if result is not None else None
        return result

    _patch(session, pubmed_interface, "search_pubmed_articles", recording_search)

    original_details = pubmed_interface.fetch_article_details

    def recording_details(self: Any, pubmed_ids: Any) -> Any:
        key = _pmid_key(pubmed_ids)
        session.used["details"].add(key)
        if resume and key in cassettes.details:
            session.reused_calls += 1
            return _records_to_df(cassettes.details[key], _JOIN_KEY_COLUMNS[DETAILS_CASSETTE])
        result = original_details(self, pubmed_ids)
        session.live_calls += 1
        cassettes.details[key] = _df_to_records(result)
        return result

    _patch(session, pubmed_interface, "fetch_article_details", recording_details)

    original_fulltext = pubmed_interface.fetch_full_text

    def recording_fulltext(
        self: Any, pmids: Any, access_token: Any = None, library_number: Any = None
    ) -> Any:
        key = _pmid_key(pmids)
        session.used["fulltext"].add(key)
        if resume and key in cassettes.fulltext:
            session.reused_calls += 1
            return _records_to_df(cassettes.fulltext[key], _JOIN_KEY_COLUMNS[FULLTEXT_CASSETTE])
        result = original_fulltext(self, pmids, access_token, library_number)
        session.live_calls += 1
        cassettes.fulltext[key] = _df_to_records(result)
        return result

    _patch(session, pubmed_interface, "fetch_full_text", recording_fulltext)


def _install_replayers(
    session: ReplaySession, workflow_handler: type, pubmed_interface: type
) -> None:
    """Replace the real seams with cassette-backed doubles."""
    cassettes = session.cassettes
    replay_model_cls = _build_replay_chat_model(on_miss=session.record_miss)

    def replay_init_openai(self: Any, **kwargs: Any) -> None:
        """Stand in for ``WorkflowHandler._init_openai``.

        Every workflow inherits this one method and calls it identically, which
        makes it the single patch point for the whole LLM surface.
        """
        self.llm_interface = replay_model_cls(cassette=cassettes.llm)
        self.openai_compatible_endpoint = kwargs.get("openai_compatible_endpoint")
        self.openai_compatible_key = kwargs.get("openai_compatible_key")
        self.openai_compatible_model = kwargs.get("openai_compatible_model")
        if kwargs.get("name") is not None:
            self.name = kwargs["name"]

    _patch(session, workflow_handler, "_init_openai", replay_init_openai)

    def _lookup(store: dict[str, Any], key: str, what: str) -> Any:
        if key not in store:
            session.record_miss(f"{what} (hash {key})")
            raise KeyError(
                f"replay cassette miss for {what} (hash {key}). The pipeline made a "
                "call that was not recorded; re-record with scripts/record_demo.py."
            )
        return store[key]

    def replay_search(self: Any, query: str) -> Any:
        return _lookup(cassettes.search, _sha(query), "PubMed search")

    _patch(session, pubmed_interface, "search_pubmed_articles", replay_search)

    def replay_details(self: Any, pubmed_ids: Any) -> Any:
        records = _lookup(cassettes.details, _pmid_key(pubmed_ids), "PubMed article details")
        return _records_to_df(records, _JOIN_KEY_COLUMNS[DETAILS_CASSETTE])

    _patch(session, pubmed_interface, "fetch_article_details", replay_details)

    def replay_fulltext(
        self: Any, pmids: Any, access_token: Any = None, library_number: Any = None
    ) -> Any:
        records = _lookup(cassettes.fulltext, _pmid_key(pmids), "PubMed full text")
        return _records_to_df(records, _JOIN_KEY_COLUMNS[FULLTEXT_CASSETTE])

    _patch(session, pubmed_interface, "fetch_full_text", replay_fulltext)


def install_network_guard(session: ReplaySession) -> None:
    """Block outbound connections and DNS, counting every attempt.

    Install this *after* ``app.server`` is imported and before the pipeline
    runs. ``TestClient`` speaks ASGI in-process, so a correct demo run makes no
    outbound connection at all.

    The guard is applied at the *connect* boundary rather than to the ``socket``
    constructor. Blocking construction outright also breaks
    ``socket.socketpair()``, which asyncio uses to build the event loop's
    self-pipe -- that would take down ``TestClient`` itself rather than catching
    a network call. Connecting and resolving are the operations that actually
    reach the network; creating a local socket pair is not.

    Patching ``getaddrinfo`` matters independently:
    ``app.v01.net_validators.validate_public_http_url`` calls it directly on
    every request to check the submitted endpoint.

    Args:
        session: The active replay session; blocked attempts are counted on it.
    """

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        session.blocked_calls += 1
        raise NetworkBlocked("network access is blocked in demo mode")

    for name in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex"):
        _patch(session, socket, name, blocked)
    for name in ("connect", "connect_ex"):
        _patch(session, socket.socket, name, blocked)
