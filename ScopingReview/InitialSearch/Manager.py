import tempfile
from abc import abstractmethod
import pandas as pd
from io import BytesIO

import ScopingReview_config.config as lit_config
import streamlit as st
from ScopingReview.BaseManager import BaseManager
from aiweb_common.resource.PubMedInterface import PubMedInterface
from fastapi import HTTPException

from typing import List


class BaseSearchManager(BaseManager):
    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.query = ""
        self.previous_query = ""
        self.pubmed_interface = PubMedInterface()

    def _fetch_articles(self, query):
        article_ids = self.pubmed_interface.search_pubmed_articles(query)
        articles_df = self.pubmed_interface.fetch_article_details(article_ids)
        articles_df = self.make_initial_df(article_ids)
        return articles_df
    
    @abstractmethod
    def _write_search_results(self, articles_df, query, query_string):
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    def get_filename(self):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_mime_type(self):
        return lit_config.EXCEL_MIME

    # def make_query(self):
    #     return self.research_q

    # def perform_search(self, search_string):
    #     articles_df = self._fetch_articles(search_string)
    #     return articles_df

    # def search_loop(self):
    #     while (len(self.article_ids) < lit_config.MIN_ARTICLES) and (self.loop_counter < lit_config.MAX_TRIES):
    #         query_string = self.generate_and_refine_query()
    #         articles_df = self.perform_search(query_string)
    #     return articles_df, query_string

    # def search_and_compile_articles(self, write_excel=True):
    #     articles_df, query_string = self.search_loop()
    #     if write_excel:
    #         self._write_search_results(articles_df, self.make_query(), query_string)
    #     return articles_df

class FastAPISearchManager(BaseSearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)

    def _write_search_results(self, articles_df, query, query_string):
        articles_df.drop_duplicates(subset="PMID")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            self.write_search_excel_output(tmpfile, articles_df, query, query_string)
        return tmpfile.name

    # def search_and_compile_articles(self, write_excel=False):
    #     articles_df, query_string = self.search_loop()
    #     if write_excel and articles_df is not None:
    #         filename = self._write_search_results(articles_df, self.make_query(), query_string)
    #         return filename
    #     return articles_df
    
    # def perform_search(self, search_string):
    #     articles_df = super().perform_search(search_string)
    #     if articles_df is not None:
    #         return articles_df
    #     return None
    
#TODO Add back later
# class StreamlitSearchManager(BaseSearchManager):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if "lock" not in st.session_state:
#             st.session_state["lock"] = False

#     def _write_search_results(self, articles_df, query, query_string):
#         articles_df.drop_duplicates(subset="PMID")
#         st.balloons()
#         with tempfile.NamedTemporaryFile(delete=True, suffix=".xlsx") as tmpfile:
#             self.write_search_excel_output(tmpfile, articles_df, query, query_string)
#             with open(tmpfile.name, "rb") as file:
#                 st.download_button(
#                     label="Download Excel file",
#                     data=file,
#                     file_name=self.get_filename(),
#                     mime=self.get_mime_type(),
#                 )

#     def get_filename(self):
#         return lit_config.SR_STEP1_FILENAME

#     def search_and_compile_articles(self, write_excel=True):
#         if st.session_state.get("lock", False):
#             return False
#         st.session_state["lock"] = True
#         articles_df, query_string = self.search_loop()
#         if write_excel:
#             self._write_search_results(articles_df, self.make_query(), query_string)
#         st.session_state["search_finished"] = True
#         st.session_state["lock"] = False
#         return st.session_state.get("search_finished", False)

#     def generate_and_refine_query(self):
#         with st.spinner("Generating pubmed search string."):
#             super().generate_and_refine_query()
#         st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
#         return self.search_string
    
#     def _cleanup_session(self):
#         keys_to_keep = {"lock", "total_cost"}
#         for key in list(st.session_state.keys()):
#             if key not in keys_to_keep:
#                 del st.session_state[key]





