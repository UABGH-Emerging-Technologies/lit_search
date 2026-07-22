# The provided code defines a base search manager class and a FastAPI search manager class for
# handling search operations in a scoping review application.
import tempfile
from abc import abstractmethod
from io import BytesIO
from typing import List

import pandas as pd
from aiweb_common.resource.PubMedInterface import PubMedInterface
from ScopingReview_config import config
from fastapi import HTTPException

import ScopingReview_config.config as config
import streamlit as st
from ScopingReview.BaseManager import BaseManager


class BaseSearchManager(BaseManager):
    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.query = ""
        self.previous_query = ""
        self.pubmed_interface = PubMedInterface(max_results=config.MAX_ARTICLES_SR)

    def _fetch_articles(self, query):
        article_ids = self.pubmed_interface.search_pubmed_articles(query)
        articles_df = self.pubmed_interface.fetch_article_details(article_ids)
        articles_df = self.make_initial_df(articles_df)
        return articles_df

    def _get_filename(self):
        return config.SR_STEP1_FILENAME

    def _get_mime_type(self):
        return config.EXCEL_MIME


class FastAPISearchManager(BaseSearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)


# TODO Add back later
class StreamlitSearchManager(BaseSearchManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "lock" not in st.session_state:
            st.session_state["lock"] = False
    def search_loop(self):
        query_string = self.generate_and_refine_query()
        articles_df = self._fetch_articles(query_string)
        return articles_df, query_string

    def _write_search_results(self, articles_df, query, query_string):
        articles_df.drop_duplicates(subset="PMID")
        st.balloons()
        with tempfile.NamedTemporaryFile(delete=True, suffix=".xlsx") as tmpfile:
            self.write_excel_output(tmpfile, articles_df, query, query_string)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=self.get_filename(),
                    mime=self.get_mime_type(),
                )

    def get_filename(self):
        return config.SR_STEP1_FILENAME

    def get_mime_type(self):
        return self._get_mime_type()

    def search_and_compile_articles(self, write_excel=True):
        if st.session_state.get("lock", False):
            return False
        st.session_state["lock"] = True
        articles_df, query_string = self.search_loop()
        if write_excel:
            self._write_search_results(articles_df, self.generate_and_refine_query(), query_string)
        st.session_state["search_finished"] = True
        st.session_state["lock"] = False
        return articles_df

    def generate_and_refine_query(self):
        with st.spinner("Generating pubmed search string."):
            # Removed call to super() as it does not exist
            query_string = self.research_q
        st.write(f"**Searching Pubmed with the query:** _{query_string}_")
        return query_string

    def _cleanup_session(self):
        keys_to_keep = {"lock", "total_cost"}
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
