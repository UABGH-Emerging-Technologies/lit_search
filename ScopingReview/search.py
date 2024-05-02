import tempfile

import pandas as pd

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


class SearchManager:
    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.query = ""
        self.pm_connection = None
        self.previous_query = ""
        st.session_state["lock"] = False

    def _fetch_articles(self, query):
        pm_connection, article_ids = search_and_compile(query, self.article_ids)
        articles_df = pm_connection.fetch_article_details(article_ids)
        articles_df = make_initial_df(pm_connection, article_ids)
        return articles_df

    def _write_search_results(self, articles_df, query, query_string):
        # dedup by PMID
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
        # default implementation, subclasses MUST override this method to work
        pass

    def get_mime_type(self):
        return lit_config.EXCEL_MIME

    def _cleanup_session(self):
        for key in st.session_state.keys():
            del st.session_state[key]

    def make_query(self):
        # default implementation, subclasses can override this method
        return self.research_q

    def generate_and_refine_query(self):
        with st.spinner("Generating pubmed search string."):
            (
                cost,
                self.loop_counter,
                self.previous_query,
                self.search_string,
            ) = make_and_refine_query(self.previous_query, self.make_query(), self.loop_counter)
        st.session_state["total_cost"] += cost
        st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
        return self.search_string

    def perform_search(self, search_string):
        self.pm_connection, self.article_ids = search_and_compile(search_string, self.article_ids)
        articles_df = self._fetch_articles(search_string)
        return articles_df

    def search_loop(self):
        while (len(self.article_ids) < lit_config.MIN_ARTICLES) and (
            self.loop_counter < lit_config.MAX_TRIES
        ):
            query_string = self.generate_and_refine_query()
            articles_df = self.perform_search(query_string)

        return articles_df, query_string

    def search_and_compile_articles(self, write_excel=True):
        if st.session_state["lock"]:  # If the lock is True, then return False
            return False

        st.session_state["lock"] = True  # Set the lock variable to True before starting the search
        articles_df, query_string = self.search_loop()

        if write_excel:
            self._write_search_results(articles_df, self.make_query(), query_string)

            st.session_state["search_finished"] = True
            st.session_state["lock"] = (
                False  # Set the lock variable to False after finishing the search
            )

            return st.session_state["search_finished"]
        else:
            return articles_df


class ArticleSearchManager(SearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)

    def get_filename(self):
        return lit_config.SR_STEP1_FILENAME


class IterateSearchManager(SearchManager):
    def __init__(self, df, research_q):
        print("Reinitializing IterateSearchManager")
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = get_relevant_rows(df)
        # print("Session State init ISM- ", st.session_state)
        if "query_terms" not in st.session_state:
            print("Initializing query terms")
            st.session_state["query_terms"] = []
            st.session_state["primary_keywords"] = []
            st.session_state["secondary_keywords"] = []
            st.session_state["exclusion_keywords"] = []
        else:
            ("Pulling query terms from session")
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

    def make_initial_query(self):
        with st.spinner("Extracting and grouping keywords from uploaded file"):
            if not st.session_state["keywords_finalized"]:
                generated_keywords_json, response_meta = generate_keywords(self.df, self.research_q)
                (
                    self.primary_keywords,
                    self.secondary_keywords,
                    self.exclusion_keywords,
                ) = parse_keywords(str(generated_keywords_json))
                self.query_terms = self.primary_keywords + self.secondary_keywords
                print("Succesfully made initial query (pks) - ", self.primary_keywords)
                st.session_state["total_cost"] += response_meta.total_cost
                return ", ".join(self.query_terms)

    def make_query(self):
        if "query_terms" not in st.session_state:
            st.write("Initlization failure - try again")
        else:
            print("query made")
            return [st.session_state["query_terms"]]

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
                print("keywords finalized session state = ", st.session_state)

    def perform_search(self, search_string):
        # Reindex dataframes and Append new results to it
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df = super().perform_search(search_string)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        # Remove duplicates based on the 'PMID' column
        articles_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        return articles_df

    def get_filename(self):
        return lit_config.SR_STEP2_FILENAME

    def _write_search_results(self, articles_df, query, query_string):
        # Reindex dataframes and Append new results to it
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df.reset_index(drop=True, inplace=True)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        # Remove duplicates based on the 'PMID' column
        articles_df.drop_duplicates(subset="PMID", keep="first", inplace=True)

        # Call parent method to write the combined results to excel
        super()._write_search_results(articles_df, query, query_string)

    def manage_keyword_extraction_and_editing(self):
        if not st.session_state["keywords_extracted"]:
            self.make_initial_query()
            st.session_state["keywords_extracted"] = True

        self.edit_query_terms()


class NewsletterSearchManager(SearchManager):
    def __init__(self, scoping_step, predefined_query, research_q):
        super().__init__(scoping_step, research_q)
        self.predefined_query = predefined_query

    def make_query(self):
        # Use the predefined query instead of generating a new one
        return self.predefined_query

    def search_and_compile_articles(self):
        articles_df = self.perform_search(self.predefined_query)
        return articles_df

    def perform_search(self, search_string):
        self.pm_connection, self.article_ids = search_and_compile(search_string, self.article_ids)
        if len(self.article_ids) >= 1:  # Check if at least 1 article is found
            articles_df = self._fetch_articles(search_string)
            return articles_df
        else:
            return None  # Return None if no articles are found
