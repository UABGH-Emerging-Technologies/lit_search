import tempfile
from aiweb_common.file_operations.text_format import convert_markdown_docx
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler, extract_response_text
import ScopingReview_config.config as config
import ScopingReview_config.prompt_config as prompt_config
from ScopingReview.InitialSearch.Workflow import ArticleSearch
from ScopingReview_config.config import REASONING_EFFORT, _is_responses_api_model


class StandaloneSummary(WorkflowHandler):
    """One-step literature summary: searches PubMed, summarizes abstracts, outputs DOCX.

    Args:
        research_question: The research question to investigate.
        openai_compatible_endpoint: LLM API endpoint URL.
        openai_compatible_key: LLM API key.
        openai_compatible_model: LLM model identifier.
    """

    def __init__(
        self,
        research_question,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__()
        self.research_question = research_question
        
        # Initialize LLM with dynamic configuration (like IRB Assistant)
        _use_responses = _is_responses_api_model(openai_compatible_model)
        self._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="StandaloneSummary",
            use_responses_api=_use_responses,
            reasoning_effort=REASONING_EFFORT if _use_responses else None,
        )
        
        # Pass LLM parameters to ArticleSearch (it also needs them now)
        self.searcher = ArticleSearch(
            research_question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        
        # Use self.llm_interface instead of config.LLM_INTERFACE
        self.single_response = SingleResponseHandler(self.llm_interface)

    def format_response(self, summary, df):
        """Format the summary and article citations into a DOCX byte string.

        Args:
            summary: LLM-generated summary text.
            df: Article DataFrame with ``citation`` column.

        Returns:
            DOCX file content as bytes.
        """
        output = str(
            "# Literature summary \n\n"
            + "_"
            + str(self.research_question)
            + "_ \n\n"
            + str(summary)
            + "\n\n"
            + "## Works consulted"
            + "\n\n"
            + "\n\n".join(df.citation)
        )
        docx_data = convert_markdown_docx(output)
        return docx_data

    def assemble_standalone_prompt(self, abstracts):
        """Build the LLM prompt for a standalone literature summary.

        Args:
            abstracts: Concatenated abstract text with APA citations.

        Returns:
            Assembled LLM prompt.
        """
        print("assembling standalone prompt")
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.STANDALONE_SUMMARY_TEMPLATE,
            user_prompt=prompt_config.SUMMARIZE_HUMAN_TEMPLATE,
            question=self.research_question,
            content=abstracts,
        )
        return assembled_prompt

    def summarize_from_abstracts(self, articles_df):
        """Summarize all article abstracts into a single literature summary.

        Args:
            articles_df: DataFrame with ``citation`` and ``abstract`` columns.

        Returns:
            LLM response object containing the summary.
        """
        article_abstracts = []
        for _, row in articles_df.iterrows():
            single_abstract = f"APA Citation: {row.citation}\n\n Abstract: {row.abstract}\n\n --- "
            article_abstracts.append(single_abstract)
        text_to_summarize = "\n\n".join(article_abstracts)
        standalone_prompt = self.assemble_standalone_prompt(text_to_summarize)
        summary, response_meta = self.single_response.generate_response(standalone_prompt)
        self._update_total_cost(response_meta)
        return summary

    def process(self):
        """Run the full standalone summary workflow: search, summarize, output DOCX.

        Returns:
            Path to the temporary DOCX file, or ``None`` on failure.
        """
        articles_df = self.searcher.process()
        self.total_cost += self.searcher.total_cost
        summary_body = self.summarize_from_abstracts(articles_df)
        docx_data = self.format_response(extract_response_text(summary_body.content), articles_df)
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None