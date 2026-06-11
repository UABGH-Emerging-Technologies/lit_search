# The provided code defines a base search manager class and a FastAPI search manager class for
# handling search operations in a scoping review application.
import tempfile
from abc import abstractmethod
from io import BytesIO
from typing import List

import pandas as pd
from aiweb_common.resource.PubMedInterface import PubMedInterface
from fastapi import HTTPException

import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager


class BaseSearchManager(BaseManager):
    """Manages PubMed article search and retrieval for a scoping review step.

    Extends :class:`BaseManager` with PubMed-specific search capabilities
    including query execution, article fetching, and result formatting.

    Args:
        scoping_step: Identifier for the current scoping review step.
        research_q: The research question driving the literature search.
    """

    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.query = ""
        self.previous_query = ""
        self.pubmed_interface = PubMedInterface()

    def _fetch_articles(self, query):
        """Execute a PubMed query and return a formatted DataFrame of article details.

        Args:
            query: PubMed search string.

        Returns:
            DataFrame with article metadata and author-relevance columns.
        """
        article_ids = self.pubmed_interface.search_pubmed_articles(query)
        articles_df = self.pubmed_interface.fetch_article_details(article_ids)
        articles_df = self.make_initial_df(articles_df)
        return articles_df

    def _get_filename(self):
        return config.SR_STEP1_FILENAME

    def _get_mime_type(self):
        return config.EXCEL_MIME


class FastAPISearchManager(BaseSearchManager):
    """FastAPI-oriented search manager with no additional state beyond the base class."""

    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)
