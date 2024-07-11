import tempfile
from abc import abstractmethod
import pandas as pd
from io import BytesIO

import ScopingReview_config.config as lit_config
import streamlit as st
from ScopingReview.data import (
    get_relevant_rows,
    get_unique_keywords,
    make_and_refine_query,
    make_initial_df,
    parse_keywords,
    search_and_compile,
    write_excel_output,
)
from ScopingReview.generate import generate_keywords

from fastapi import UploadFile, HTTPException

from pydantic import BaseModel
from typing import List


# TODO: I'm pretty sure I've broken the streamlit impelmentation
# specifically, I'm concerned about how `edit_query_terms` works



class BaseSearchManager:
    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.query = ""
        self.previous_query = ""
        self.total_cost = 0 

    def _fetch_articles(self, query):
        pm_connection, article_ids = search_and_compile(query, self.article_ids)
        articles_df = pm_connection.fetch_article_details(article_ids)
        articles_df = make_initial_df(pm_connection, article_ids)
        return articles_df
    
    @abstractmethod
    def _write_search_results(self, articles_df, query, query_string):
        # This method needs to be implemented by subclasses to handle output.
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    def get_filename(self):
        # This should be implemented to provide a filename for downloads.
        raise NotImplementedError("Subclasses must implement this method.")

    def get_mime_type(self):
        return lit_config.EXCEL_MIME

    def make_query(self):
        # default implementation, subclasses can override this method
        return self.research_q

    def generate_and_refine_query(self):
        cost, self.loop_counter, self.previous_query, self.search_string = \
            make_and_refine_query(self.previous_query, self.make_query(), self.loop_counter)
        self.total_cost += cost
        return self.search_string

    # TODO: _fetch_articles does search_and_compile
    # where does it join with previous articles?
    def perform_search(self, search_string):
        articles_df = self._fetch_articles(search_string)
        return articles_df

    def search_loop(self):
        while (len(self.article_ids) < lit_config.MIN_ARTICLES) and (self.loop_counter < lit_config.MAX_TRIES):
            query_string = self.generate_and_refine_query()
            articles_df = self.perform_search(query_string)
        return articles_df, query_string

    def search_and_compile_articles(self, write_excel=True):
        articles_df, query_string = self.search_loop()
        if write_excel:
            self._write_search_results(articles_df, self.make_query(), query_string)
        return articles_df


class StreamlitSearchManager(BaseSearchManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "lock" not in st.session_state:
            st.session_state["lock"] = False

    def _write_search_results(self, articles_df, query, query_string):
        articles_df.drop_duplicates(subset="PMID")
        st.balloons()
        with tempfile.NamedTemporaryFile(delete=True, suffix=".xlsx") as tmpfile:
            write_excel_output(tmpfile, articles_df, query, query_string)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=self.get_filename(),
                    mime=self.get_mime_type(),
                )

    def get_filename(self):
        return "search_results.xlsx"  # Default implementation, can be overridden as needed.


    def search_and_compile_articles(self, write_excel=True):
        if st.session_state.get("lock", False):
            return False
        st.session_state["lock"] = True
        articles_df, query_string = self.search_loop()
        if write_excel:
            self._write_search_results(articles_df, self.make_query(), query_string)
        st.session_state["search_finished"] = True
        st.session_state["lock"] = False
        if "cost" not in st.session_state:
            st.session_state["total_cost"] = self.total_cost
        else:
            st.session_state["total_cost"] += self.total_cost
        return st.session_state.get("search_finished", False)

    def generate_and_refine_query(self):
        with st.spinner("Generating pubmed search string."):
            super().generate_and_refine_query()
        st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
        return self.search_string
    
    def _cleanup_session(self):
        keys_to_keep = {"lock", "total_cost"}  # Preserving certain states if needed.
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]

# keeping name for compatibility with previous implementations
# eventually want this name to begin with Streamlit...
class ArticleSearchManager(StreamlitSearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)

    def get_filename(self):
        return lit_config.SR_STEP1_FILENAME
    
class BaseIterateSearchManager(BaseSearchManager):
    def __init__(self, df, research_q):
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = get_relevant_rows(df)
        self.query_terms = []
        self.primary_keywords = []
        self.secondary_keywords = []
        self.exclusion_keywords = []
        self.keywords_extracted = False  # Initialize the flag here
        
    def get_filename(self):
        return lit_config.SR_STEP2_FILENAME
    

    def initialize_keywords(self, primary, secondary, exclusion):
        self.primary_keywords = primary
        self.secondary_keywords = secondary
        self.exclusion_keywords = exclusion
        self.query_terms = self.primary_keywords + self.secondary_keywords

    def make_initial_query(self):
        # This function would generate keywords without interaction
        # Returns initial keywords and total cost
        generated_keywords_json, response_meta = generate_keywords(self.df, self.research_q)
        (
            self.primary_keywords,
            self.secondary_keywords,
            self.exclusion_keywords,
        ) = parse_keywords(str(generated_keywords_json))
        self.initialize_keywords(self.primary_keywords, self.secondary_keywords, self.exclusion_keywords)
        return ", ".join(self.query_terms), response_meta.total_cost

    def make_query(self):
        return self.query_terms

    def perform_search(self, search_string):
        # Reindex dataframes and Append new results to it
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df = super().perform_search(search_string)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        # Remove duplicates based on the 'PMID' column
        articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)

        return articles_df

    def manage_keyword_extraction(self):
        # Method to handle the initial extraction and keyword editing
        if not self.keywords_extracted:
            initial_query, cost = self.make_initial_query()
            self.total_cost += cost
            self.keywords_extracted = True
        return initial_query

# keeping name for compatibility with previous implementations
# eventually want this name to begin with Streamlit...
class IterateSearchManager(BaseIterateSearchManager):
    def __init__(self, df, research_q):
        super().__init__(df, research_q)
        self.setup_streamlit_session()

    def setup_streamlit_session(self):
        if "query_terms" not in st.session_state:
            print("Initializing query terms")
            st.session_state["query_terms"] = []
            st.session_state["primary_keywords"] = []
            st.session_state["secondary_keywords"] = []
            st.session_state["exclusion_keywords"] = []
        else:
            print("Pulling query terms from session")
            self.query_terms = st.session_state["query_terms"]
            self.primary_keywords = [
                keyword.strip() for keyword in str(st.session_state["primary_keywords"]).split(",")
            ]
            self.secondary_keywords = [
                keyword.strip()
                for keyword in str(st.session_state["secondary_keywords"]).split(",")
            ]
            self.exclusion_keywords = [
                keyword.strip()
                for keyword in str(st.session_state["exclusion_keywords"]).split(",")
            ]

# TODO: The `make_initial_query` naming throughout this file confused me. -RM
    def make_initial_query(self):
        with st.spinner("Extracting and grouping keywords from uploaded file"):
            initial_query, cost = super().make_initial_query()
            self.total_cost += cost
            return initial_query

    def edit_query_terms(self):
        with st.form("my_form"):
            st.session_state["primary_keywords"] = st.text_area(
                "Primary Keywords (comma-separated):", ", ".join(self.primary_keywords)
            )
            st.session_state["secondary_keywords"] = st.text_area(
                "Secondary Keywords (comma-separated):", ", ".join(self.secondary_keywords)
            )
            st.session_state["exclusion_keywords"] = st.text_area(
                "Exclusion Keywords (comma-separated):", ", ".join(self.exclusion_keywords)
            )

            keywords_submitted = st.form_submit_button("Looks good!")
            if keywords_submitted:
                self.query_terms = (
                    "Primary topics to include in query: "
                    + st.session_state["primary_keywords"]
                    + ".  Secondary topics to include in query: "
                    + st.session_state["secondary_keywords"]
                    + ".  Here's a set of topics to exclude in query contstruction "
                    + st.session_state["exclusion_keywords"]
                )
                st.session_state["query_terms"] = self.query_terms
                st.session_state["keywords_finalized"] = True
                if "cost" not in st.session_state:
                    st.session_state["total_cost"] = self.total_cost
                else:
                    st.session_state["total_cost"] += self.total_cost
                print("Keywords finalized session state = ", st.session_state)


class NewsletterSearchManager(BaseSearchManager):
    def __init__(self, scoping_step, predefined_query, research_q):
        super().__init__(scoping_step, research_q)
        self.predefined_query = predefined_query

    def make_query(self):
        # Uses the predefined query instead of generating a new one
        return self.predefined_query

    def search_and_compile_articles(self):
        articles_df = self.perform_search(self.predefined_query)
        return articles_df

    def perform_search(self, search_string):
        articles_df = self._fetch_articles(search_string)
        return articles_df


class FastAPISearchManager(BaseSearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)

    def _write_search_results(self, articles_df, query, query_string):
        # Deduplicate by PMID and write to Excel with a more persistent file handling for API response
        articles_df.drop_duplicates(subset="PMID")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            write_excel_output(tmpfile, articles_df, query, query_string)
        return tmpfile.name

    def search_and_compile_articles(self, write_excel=False):
        articles_df, query_string = self.search_loop()
        if write_excel and articles_df is not None:
            filename = self._write_search_results(articles_df, self.make_query(), query_string)
            return filename, self.total_cost
        return articles_df, self.total_cost
    
    def perform_search(self, search_string):
        # Calls the base class method to perform the search and handle no-article-found scenario
        articles_df = super().perform_search(search_string)
        if articles_df is not None:
            return articles_df
        return None  # Return None if no articles are found, suitable for API responses


class FastAPIIterateSearchManager(BaseIterateSearchManager):
    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)
        
    def extract_and_return_keywords(self) -> KeywordsData:
        try:
            initial_query = self.manage_keyword_extraction() 
            return KeywordsData(
                primary_keywords=self.primary_keywords,
                secondary_keywords=self.secondary_keywords,
                exclusion_keywords=self.exclusion_keywords
            ), self.total_cost
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    def edit_query_terms(self):
        self.query_terms = (
                self.research_q +
                "\n\n Primary topics to include in query: " + ", ".join(self.primary_keywords) +
                ". Secondary topics to include in query: " + ", ".join(self.secondary_keywords) +
                ". Here's a set of topics to exclude in query construction: " + ", ".join(self.exclusion_keywords)
            )
        self.search_string = self.generate_and_refine_query()
        print(self.search_string)
        return self.search_string


    def update_keywords_and_perform_search(self, keywords: KeywordsData) -> str:
        try:
            self.initialize_keywords(keywords.primary_keywords, keywords.secondary_keywords, keywords.exclusion_keywords)
            # This was done by edit_keywords in the streamlit implementation
            # Not sure if there's benefit to breaking it off here.

            query = self.edit_query_terms()
            print(query)
            articles_df = self.perform_search(query)
            if articles_df is None or articles_df.empty:
                raise HTTPException(status_code=404, detail="No articles found with the revised keywords")
            temp_file_path = self.save_results_to_excel(articles_df)
            return temp_file_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    def save_results_to_excel(self, df: pd.DataFrame) -> str:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
                df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to save Excel file") from e