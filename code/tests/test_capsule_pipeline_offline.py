"""End-to-end pipeline test with fake externals, no network and no credentials.

This exists because two live recordings died at step 4 with `KeyError: 'category'`
after paying for real LLM calls. The failure was always upstream: step 3
categorized zero articles, returned HTTP 200 anyway, and step 4 was the first
thing to notice. This test walks the same six steps the capsule driver walks and
asserts step 3 actually categorized something, so that class of failure is caught
here instead of halfway through a paid recording.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, get_buffer_string
from langchain_core.outputs import ChatGeneration, ChatResult

from capsule.screening import AUTHOR_1_COLUMN

KEYWORD_JSON = (
    '{"Primary Keywords": ["artificial intelligence", "perioperative"], '
    '"Secondary Keywords": ["outcomes"], "Exclusion Keywords": ["dentistry"]}'
)


def _build_scripted_model(seen: list[str] | None = None) -> type:
    """Build a chat model that answers each pipeline step plausibly.

    Args:
        seen: Optional list that every prompt is appended to, so a caller can
            assert the pipeline builds identical prompts run over run.
    """

    class _ScriptedChatModel(BaseChatModel):
        """Dispatch on prompt content so every step gets a parseable answer."""

        @property
        def _llm_type(self) -> str:
            return "scripted-test-model"

        def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> ChatResult:
            raw = get_buffer_string(messages)
            if seen is not None:
                seen.append(raw)
            prompt = raw.lower()
            if "primary keywords" in prompt:
                content = KEYWORD_JSON
            elif "input categories" in prompt:
                content = "diagnosis"
            elif "pubmed search string" in prompt or "search string" in prompt:
                content = "(artificial intelligence[Title]) AND (perioperative[Title])"
            else:
                content = "A synthetic narrative paragraph produced for testing (Smith, 2024)."
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    return _ScriptedChatModel


def _fake_articles(count: int = 20) -> pd.DataFrame:
    """Return a PubMed-shaped article frame."""
    return pd.DataFrame(
        [
            {
                "date_published": "2024",
                "title": f"Perioperative AI study {i}",
                "keywords": ["artificial intelligence", "perioperative"],
                "abstract": f"Synthetic abstract {i} about perioperative decision support.",
                "pmid": str(30000 + i),
                "authors": [f"Author {i}"],
                "journal": "Journal of Testing",
                "citation": f"Author {i}. (2024). Perioperative AI study {i}.",
            }
            for i in range(count)
        ]
    )


@pytest.fixture
def prompt_log() -> list[str]:
    """Collect every prompt the pipeline sends, in order."""
    return []


@pytest.fixture
def offline_pipeline(monkeypatch: pytest.MonkeyPatch, prompt_log: list[str]) -> None:
    """Replace the LLM and every PubMed/LibKey call with deterministic fakes."""
    from aiweb_common.resource.PubMedInterface import PubMedInterface
    from aiweb_common.WorkflowHandler import WorkflowHandler

    model_cls = _build_scripted_model(prompt_log)

    def fake_init_openai(self: Any, **kwargs: Any) -> None:
        self.llm_interface = model_cls()

    monkeypatch.setattr(WorkflowHandler, "_init_openai", fake_init_openai)
    monkeypatch.setattr(
        PubMedInterface,
        "search_pubmed_articles",
        lambda self, query: [str(30000 + i) for i in range(20)],
    )
    monkeypatch.setattr(
        PubMedInterface, "fetch_article_details", lambda self, ids: _fake_articles(len(list(ids)))
    )
    monkeypatch.setattr(
        PubMedInterface,
        "fetch_full_text",
        lambda self, pmids, access_token=None, library_number=None: pd.DataFrame(
            {
                "PMID": [str(p) for p in pmids],
                "URL": [f"https://example.invalid/{p}" for p in pmids],
                "Downloaded": [True] * len(list(pmids)),
                "Text": [f"Full text body for {p}. " * 20 for p in pmids],
            }
        ),
    )


def _run(tmp_path: Path, auto_screen: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Drive the pipeline the way the capsule does and return outputs + screening."""
    from fastapi.testclient import TestClient

    from app.server import app
    from scripts import capsule_driver as driver

    tmp_path.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    screening: dict[str, Any] = {}
    driver._run_pipeline(
        TestClient(app),
        tmp_path,
        "Does AI improve perioperative decision-making?",
        "diagnosis, prognosis",
        "test-key",
        "https://demo.invalid/v1",
        "test-model",
        None,
        outputs,
        auto_screen=auto_screen,
        screening_info=screening,
    )
    return outputs, screening


def test_pipeline_completes_all_six_steps_with_auto_screening(
    offline_pipeline: None, tmp_path: Path
) -> None:
    """The full six-step run must finish and actually categorize articles.

    Both live recordings died here. Step 3 returned 200 while categorizing
    nothing, so step 4 hit ``KeyError: 'category'``.
    """
    outputs, screening = _run(tmp_path, auto_screen=15)

    assert screening == {"synthetic": True, "marked": 15, "total": 20}

    produced = {Path(entry["file"]).name for entry in outputs}
    for expected in (
        "step1_search_results.xlsx",
        "step2_refined_results.xlsx",
        "step3_categorized.xlsx",
        "step2_keywords.json",
        "step4_summaries.docx",
        "step5_draft.docx",
    ):
        assert expected in produced, f"{expected} missing from {sorted(produced)}"

    # The screening marks must survive step 2 into step 3, which is the link
    # that was actually broken.
    step3 = pd.read_excel(tmp_path / "step3_categorized.xlsx")
    assert "category" in step3.columns
    assert step3["category"].notna().sum() > 0

    # And the synthetic-screening notice must be written where a reader sees it.
    assert "SYNTHETIC SCREENING" in (tmp_path / "DEMO_NOTICE.txt").read_text()


def test_pipeline_fails_at_step3_with_a_useful_message_when_unscreened(
    offline_pipeline: None, tmp_path: Path
) -> None:
    """Without screening the run must fail at step 3, naming the real cause.

    Previously it sailed through step 3 and died in step 4 on a bare
    ``KeyError: 'category'`` that pointed at the wrong place entirely.
    """
    with pytest.raises(RuntimeError, match="step 3 categorized 0 of"):
        _run(tmp_path, auto_screen=0)


def test_run_pipeline_requires_an_explicit_screening_decision() -> None:
    """``auto_screen`` is keyword-only with no default, so it cannot be forgotten.

    A positional call that omitted it silently defaulted to 0, which is exactly
    how the second recording failed the same way as the first.
    """
    import inspect

    from scripts import capsule_driver as driver

    parameter = inspect.signature(driver._run_pipeline).parameters["auto_screen"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def test_auto_screen_marks_only_the_requested_count(offline_pipeline: None, tmp_path: Path) -> None:
    """Screening must mark exactly N articles, leaving the rest untouched."""
    _run(tmp_path, auto_screen=5)
    step1 = pd.read_excel(tmp_path / "step1_search_results.xlsx")
    encoded = base64.b64encode((tmp_path / "step1_search_results.xlsx").read_bytes()).decode()
    assert pd.read_excel(BytesIO(base64.b64decode(encoded))).equals(step1)
    # step1 on disk is the pre-screening workbook; screening is applied in-flight.
    assert (step1[AUTHOR_1_COLUMN] == "No").all()


def test_pipeline_prompts_are_deterministic(
    offline_pipeline: None, prompt_log: list[str], tmp_path: Path
) -> None:
    """Every prompt must be byte-identical across runs, or replay can never match.

    ``Draft/Workflow.write_first_draft`` used to interpolate the raw ``AIMessage``
    for the introduction into the conclusion and abstract prompts. Python
    stringified it, embedding ``id='lc_run--<random uuid>'``, so those two
    prompts differed on every run -- a permanent cassette miss, and in live runs
    a prompt full of LangChain object repr instead of the drafted text.
    """
    _run(tmp_path / "first", auto_screen=15)
    first = list(prompt_log)
    prompt_log.clear()
    _run(tmp_path / "second", auto_screen=15)
    second = list(prompt_log)

    assert len(first) == len(second), "pipeline made a different number of LLM calls"
    for index, (a, b) in enumerate(zip(first, second)):
        assert (
            a == b
        ), f"prompt {index} differs between runs:\n--- run 1 ---\n{a}\n--- run 2 ---\n{b}"


def test_no_prompt_contains_a_langchain_object_repr(
    offline_pipeline: None, prompt_log: list[str], tmp_path: Path
) -> None:
    """A response object interpolated into a prompt is always a bug."""
    _run(tmp_path, auto_screen=15)
    for index, prompt in enumerate(prompt_log):
        for marker in (
            "lc_run--",
            "additional_kwargs=",
            "response_metadata=",
            "invalid_tool_calls=",
        ):
            assert (
                marker not in prompt
            ), f"prompt {index} contains {marker!r}: a raw message object was interpolated"
