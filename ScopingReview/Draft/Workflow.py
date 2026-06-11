import tempfile

from aiweb_common.file_operations.text_format import convert_markdown_docx
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler, extract_response_text

import ScopingReview_config.boilerplate as boilerplate_config
import ScopingReview_config.prompt_config as prompt_config
from ScopingReview.Draft.Manager import DraftReviewManager
from ScopingReview_config import config
from ScopingReview_config.config import (
    REASONING_EFFORT,
    _is_responses_api_model,
)


class DraftReview(WorkflowHandler):
    """Generates a first draft of a scoping review from category summaries.

    Produces introduction, conclusion, and abstract sections via LLM, then
    assembles them with a boilerplate methodology and the original results.

    Args:
        summaries: Markdown string of all category summaries.
        research_q: The research question.
        openai_compatible_endpoint: LLM API endpoint URL.
        openai_compatible_key: LLM API key.
        openai_compatible_model: LLM model identifier.
    """

    def __init__(
        self,
        summaries,
        research_q,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__()
        self.summaries = summaries
        self.research_q = research_q
        self.drafter = DraftReviewManager(summaries, research_q)

        # Initialize LLM with dynamic configuration (like IRB Assistant)
        _use_responses = _is_responses_api_model(openai_compatible_model)
        self._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="DraftReview",
            use_responses_api=_use_responses,
            reasoning_effort=REASONING_EFFORT if _use_responses else None,
        )

        # Use self.llm_interface instead of config.LLM_INTERFACE
        self.single_response = SingleResponseHandler(self.llm_interface)

    def draft_review(self):
        """Generate the full draft if summaries are available.

        Returns:
            Assembled draft markdown string, or ``None`` if no summaries.
        """
        if self.summaries is not None:
            markdown_to_convert = self.write_first_draft()
            return markdown_to_convert

    def assemble_intro_prompt(self, summaries_no_bib):
        """Build the LLM prompt for drafting the introduction section.

        Args:
            summaries_no_bib: List of summary paragraphs without bibliography lines.

        Returns:
            Assembled LLM prompt.
        """
        print("assembling intro prompt")
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.SYSTEM_DRAFT_TEMPLATE,
            user_prompt=prompt_config.HUMAN_INTRODUCTION_TEMPLATE,
            question=self.research_q,
            summaries="\n\n".join(summaries_no_bib),
        )
        return assembled_prompt

    def assemble_conclusion_prompt(self, summaries_no_bib, intro):
        """Build the LLM prompt for drafting the conclusion section.

        Args:
            summaries_no_bib: List of summary paragraphs without bibliography lines.
            intro: The generated introduction text.

        Returns:
            Assembled LLM prompt.
        """
        print("assembling conclusion prompt")
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.SYSTEM_DRAFT_TEMPLATE,
            user_prompt=prompt_config.HUMAN_CONCLUSION_TEMPLATE,
            question=self.research_q,
            summaries="\n\n".join(summaries_no_bib),
            introduction=intro,
        )
        return assembled_prompt

    def assemble_abstract_prompt(self, summaries_no_bib, intro, conclusion):
        """Build the LLM prompt for drafting the abstract.

        Args:
            summaries_no_bib: List of summary paragraphs without bibliography lines.
            intro: The generated introduction text.
            conclusion: The generated conclusion text.

        Returns:
            Assembled LLM prompt.
        """
        print("assembling abstract prompt")
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.SYSTEM_DRAFT_TEMPLATE,
            user_prompt=prompt_config.HUMAN_ABSTRACT_TEMPLATE,
            question=self.research_q,
            summaries="\n\n".join(summaries_no_bib),
            introduction=intro,
            methodology=boilerplate_config.METHODOLOGY,
            conclusion=conclusion,
        )
        return assembled_prompt

    def write_first_draft(self):
        """Generate all draft sections via LLM and assemble the complete document.

        Returns:
            Full draft markdown string.
        """
        citations, non_citations = self.drafter.extract_apa_citations(self.summaries)
        # prep introduction
        intro_prompt = self.assemble_intro_prompt(non_citations)
        intro, intro_response_meta = self.single_response.generate_response(intro_prompt)
        self._update_total_cost(intro_response_meta)
        # prep conclusion
        conclusion_prompt = self.assemble_conclusion_prompt(non_citations, intro)
        conclusion, conclusion_response_meta = self.single_response.generate_response(
            conclusion_prompt
        )
        self._update_total_cost(conclusion_response_meta)
        # prep abstract
        abstract_prompt = self.assemble_abstract_prompt(non_citations, intro, conclusion)
        abstract, abstract_response_meta = self.single_response.generate_response(abstract_prompt)
        self._update_total_cost(abstract_response_meta)
        assembled_draft = self.drafter.assemble_document(
            abstract_md=extract_response_text(abstract.content),
            intro_md=extract_response_text(intro.content),
            methods_md=boilerplate_config.METHODOLOGY,
            results_md=non_citations,
            conclusion_md=extract_response_text(conclusion.content),
            citations_md=citations,
        )
        return assembled_draft

    def process(self):
        """Run the draft generation workflow.

        Returns:
            Full draft markdown string.
        """
        draft_md = self.draft_review()
        return draft_md
