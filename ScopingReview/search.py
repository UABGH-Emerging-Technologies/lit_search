from ScopingReview.data import make_and_refine_query, search_and_compile, write_excel_output
from ScopingReview.data import get_relevant_keywords, get_unique_keywords
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
        
    def _fetch_articles(self, query):
        pm_connection, article_ids = search_and_compile(query, self.article_ids)
        return pm_connection.fetch_article_details(article_ids)

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
        return "articles.xlsx"

    def make_query(self):
        # default implementation, subclasses can override this method
        return self.research_q

    def search_and_compile_articles(self):
        finished_search = False
        while len(self.article_ids) < review_config.MIN_ARTICLES and self.loop_counter < 6:
            with st.spinner("Generating pubmed search string."):
                self.cost, self.loop_counter, self.previous_query, self.search_string = make_and_refine_query(self.previous_query, self.make_query(), self.cost, self.loop_counter)
            
            st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
            self.pm_connection, self.article_ids = search_and_compile(self.search_string, self.article_ids)
            articles_df = self._fetch_articles(self.search_string)
            self._write_search_results(articles_df, self.make_query())
            # Check if we finished the search
            finished_search = len(self.article_ids) >= review_config.MIN_ARTICLES or self.loop_counter >= 6
            # If the search is finished, break the loop
            if finished_search:
                break
        return finished_search

class ArticleSearchManager(SearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)
        self.articles_downloaded = False
        
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
        keywords_to_requery = get_relevant_keywords(self.df)
        return get_unique_keywords(keywords_to_requery)

    def get_filename(self):
        return review_config.SR_STEP2_FILENAME


class CategorizeManager:
    def __init__(self, df, research_q):
        self.df = df
        self.research_q = research_q

    def categorize_articles(self):
        print("This is where the categorization specific logic will go")