import logging

from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler, extract_response_text

from ScopingReview.Keywords.Manager import KeywordData, KeywordManager

logger = logging.getLogger(__name__)
from ScopingReview_config import config, prompt_config
from ScopingReview_config.config import (
    REASONING_EFFORT,
    _is_responses_api_model,
)


class KeywordWorkflow(WorkflowHandler):
    """Generates primary, secondary, and exclusion keywords from article metadata via LLM.

    Args:
        df: Article DataFrame with titles and keywords.
        research_question: The research question for keyword context.
        openai_compatible_endpoint: LLM API endpoint URL.
        openai_compatible_key: LLM API key.
        openai_compatible_model: LLM model identifier.
    """

    def __init__(
        self,
        df,
        research_question,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__()
        self.df = df
        self.research_question = research_question

        # Initialize LLM with dynamic configuration (like IRB Assistant)
        _use_responses = _is_responses_api_model(openai_compatible_model)
        self._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="KeywordWorkflow",
            use_responses_api=_use_responses,
            reasoning_effort=REASONING_EFFORT if _use_responses else None,
        )

        # Use self.llm_interface instead of config.SMART_LLM_INTERFACE
        self.single_response = SingleResponseHandler(self.llm_interface)
        self.keyword_manager = KeywordManager(self.df, self.research_question)

    def initialize_keywords(self):
        """Call the LLM to generate keyword suggestions from article titles and existing keywords.

        Returns:
            Raw LLM response text containing keyword JSON.
        """
        relevant_rows = self.keyword_manager.get_relevant_rows()
        all_titles = relevant_rows["title"].tolist()
        formatted_keywords = self.keyword_manager.format_keywords(relevant_rows)
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.GENERATE_SYSTEM_KEYWORD_PROMPT,
            user_prompt=prompt_config.GENERATE_HUMAN_KEYWORD_PROMPT,
            question=self.research_question,
            titles=all_titles,
            keywords_list=formatted_keywords,
        )
        response, response_meta = self.single_response.generate_response(assembled_prompt)
        logger.debug("Response - %s", extract_response_text(response.content))
        self._update_total_cost(response_meta)
        return extract_response_text(response.content)

    def process(self):
        """Run the full keyword extraction workflow.

        Returns:
            :class:`KeywordData` with primary, secondary, and exclusion keywords.
        """
        logger.info("Generating Keywords")
        generated_keywords_json = self.initialize_keywords()
        logger.debug("Generated keywords JSON: %s", generated_keywords_json)
        primary, secondary, exclusion = self.keyword_manager.parse_keywords(
            str(generated_keywords_json)
        )
        keywords = KeywordData(
            primary_keywords=primary, secondary_keywords=secondary, exclusion_keywords=exclusion
        )
        return keywords
