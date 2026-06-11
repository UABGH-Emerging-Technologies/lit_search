import logging
import tempfile

import pandas as pd
from fastapi import HTTPException

from ScopingReview.InitialSearch.Manager import BaseSearchManager

logger = logging.getLogger(__name__)
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from ScopingReview_config import config


class BaseIterateSearchManager(BaseSearchManager):
    """Refines an initial PubMed search by incorporating extracted keywords.

    Takes the article DataFrame and keyword lists from a previous step, builds
    an enriched query prompt, and manages the iterative search-merge cycle.

    Args:
        df: Article DataFrame from the initial search.
        research_q: The research question.
        keywords: :class:`KeywordData` with primary, secondary, and exclusion lists.
        openai_compatible_endpoint: LLM API endpoint URL.
        openai_compatible_key: LLM API key.
        openai_compatible_model: LLM model identifier.
    """

    def __init__(
        self,
        df,
        research_q,
        keywords,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = self.get_relevant_rows()
        self.query_terms = []
        self.primary_keywords = keywords.primary_keywords
        self.secondary_keywords = keywords.secondary_keywords
        self.exclusion_keywords = keywords.exclusion_keywords

        # Store LLM config
        self.openai_compatible_endpoint = openai_compatible_endpoint
        self.openai_compatible_key = openai_compatible_key
        self.openai_compatible_model = openai_compatible_model

        # Pass LLM config to KeywordWorkflow
        self.keyword_workflow = KeywordWorkflow(
            self.df,
            research_question=research_q,
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def _get_filename(self):
        return config.SR_STEP2_FILENAME

    def _get_mime_type(self):
        return config.EXCEL_MIME

    def _prepare_query_with_keywords(self):
        """Build a query prompt string incorporating primary, secondary, and exclusion keywords.

        Returns:
            The assembled query prompt string.
        """
        self.query_prompt = (
            "Overall Research Question: "
            + self.research_q
            + "\n\n Primary topics to include in query: "
            + ", ".join(self.primary_keywords)
            + ". Secondary topics to include in query: "
            + ", ".join(self.secondary_keywords)
            + ". Here's a set of topics to exclude in query construction: "
            + ", ".join(self.exclusion_keywords)
        )
        logger.debug("Query prompt: %s", self.query_prompt)
        return self.query_prompt

    def determine_keywords(self):
        """Run the keyword workflow to extract new keywords from the current article set.

        Returns:
            :class:`KeywordData` with updated keyword lists.
        """
        generated_keywords = self.keyword_workflow.process()
        self.primary_keywords, self.secondary_keywords, self.exclusion_keywords = generated_keywords
        return generated_keywords

    def refine_query(self):
        """Prepare and return a keyword-enriched query prompt."""
        return self._prepare_query_with_keywords()

    def update_articles(self, articles_df):
        """Merge new articles into the existing selection, dropping duplicates by PMID.

        Args:
            articles_df: Newly fetched article DataFrame to merge.
        """
        self.selected_articles_df = pd.concat(
            [self.selected_articles_df, articles_df], ignore_index=True
        )
        self.selected_articles_df.drop_duplicates(subset="PMID", keep="first", inplace=True)


class FastAPIIterateSearchManager(BaseIterateSearchManager):
    """FastAPI-oriented iterate-search manager."""

    def __init__(
        self,
        df: pd.DataFrame,
        research_q: str,
        keywords: KeywordData,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__(
            df,
            research_q,
            keywords,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
