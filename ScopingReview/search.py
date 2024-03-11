from ScopingReview.data import make_and_refine_query, search_and_compile, write_excel_output
from ScopingReview.data import get_relevant_rows, get_unique_keywords, make_initial_df
import ScopingReview_config.config as review_config
import streamlit as st
import tempfile

class SearchManager:
    def __init__(self, scoping_step, research_q):
        self.scoping_step = scoping_step
        self.research_q = research_q
        self.article_ids = []
        self.loop_counter = 0
        self.cost = 0.0
        self.query = ""
        self.pm_connection = None
        self.previous_query = ""  
        st.session_state['lock'] = False 
        
    def _fetch_articles(self, query):
        pm_connection, article_ids = search_and_compile(query, self.article_ids)
        articles_df = pm_connection.fetch_article_details(article_ids)
        articles_df = make_initial_df(pm_connection, article_ids)  
        return articles_df

    def _write_search_results(self, articles_df, query):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            write_excel_output(tmpfile, articles_df, query)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=self.get_filename(),
                    mime="application/vnd.ms-excel"
                )

    def get_filename(self):
        # default implementation, subclasses can override this method
        return review_config.SR_STEP1_FILENAME

    def make_query(self):
        # default implementation, subclasses can override this method
        return self.research_q

    def search_and_compile_articles(self):
        if st.session_state['lock']:  # If the lock is True, then return False
            return False

        st.session_state['lock'] = True  # Set the lock variable to True before starting the search

        # Generate and refine the query
        with st.spinner("Generating pubmed search string."):
            self.cost, self.loop_counter, self.previous_query, self.search_string = make_and_refine_query(self.previous_query, self.make_query(), self.cost, self.loop_counter)

        st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
        self.pm_connection, self.article_ids = search_and_compile(self.search_string, self.article_ids)
        articles_df = self._fetch_articles(self.search_string)
        self._write_search_results(articles_df, self.make_query())

        # Check if we finished the search
        finished_search = len(self.article_ids) >= review_config.MIN_ARTICLES or self.loop_counter >= 6
        st.session_state['search_finished'] = finished_search

        st.session_state['lock'] = False  # Set the lock variable to False after finishing the search

        return finished_search

class ArticleSearchManager(SearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)
        
    def get_filename(self):
        return review_config.SR_STEP1_FILENAME

    def download_articles(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            articles_df = self._fetch_articles(self.query)
            write_excel_output(tmpfile, articles_df, self.research_q)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name="Testing.xlsx",
                    mime="application/vnd.ms-excel"
                )

class IterateSearchManager(SearchManager):
    def __init__(self, df):
        super().__init__(None, None)
        self.df = df

    def make_query(self):
        keywords_to_requery = get_relevant_rows(self.df)
        return get_unique_keywords(keywords_to_requery)

    def get_filename(self):
        return review_config.SR_STEP2_FILENAME

