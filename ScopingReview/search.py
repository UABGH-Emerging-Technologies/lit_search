from ScopingReview.data import make_and_refine_query, search_and_compile, write_excel_output
from ScopingReview.data import get_relevant_rows, make_initial_df, parse_keywords
from ScopingReview.generate import generate_keywords
import ScopingReview_config.config as review_config
import streamlit as st
import tempfile
import pandas as pd

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
        st.balloons()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            write_excel_output(tmpfile, articles_df, query)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=self.get_filename(),
                    mime=self.get_mime_type()
                )

    def get_filename(self):
        # default implementation, subclasses MUST override this method to work
        pass
    
    def get_mime_type(self):
        return review_config.EXCEL_MIME


    def make_query(self):
        # default implementation, subclasses can override this method
        return self.research_q

    def search_and_compile_articles(self):
        if st.session_state['lock']:  # If the lock is True, then return False
            return False

        st.session_state['lock'] = True  # Set the lock variable to True before starting the search

        # Generate and refine the query
        while (len(self.article_ids) < review_config.MIN_ARTICLES) and (self.loop_counter < review_config.MAX_TRIES):
            with st.spinner("Generating pubmed search string."):
                self.cost, self.loop_counter, self.previous_query, self.search_string = make_and_refine_query(self.previous_query, self.make_query(), self.cost, self.loop_counter)

            st.write(f"**Searching Pubmed with the query:** _{self.search_string}_")
            self.pm_connection, self.article_ids = search_and_compile(self.search_string, self.article_ids)
            articles_df = self._fetch_articles(self.search_string)
        
        self._write_search_results(articles_df, self.make_query())
        
        st.session_state['search_finished'] = True
        st.session_state['lock'] = False  # Set the lock variable to False after finishing the search

        return st.session_state['search_finished']

class ArticleSearchManager(SearchManager):
    def __init__(self, scoping_step, research_q):
        super().__init__(scoping_step, research_q)
        
    def get_filename(self):
        return review_config.SR_STEP1_FILENAME
    
    
class IterateSearchManager(SearchManager):
    def __init__(self, df, research_q):
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = get_relevant_rows(df)
        self.make_initial_query()
        self.iteration_count = 1

    def make_initial_query(self):
        with st.spinner("Extracting and grouping keywords from uploaded file"):
            generated_keywords_json = generate_keywords(self.df, self.research_q)
            self.primary_keywords, self.secondary_keywords, self.exclusion_keywords = parse_keywords(str(generated_keywords_json))
            self.query_terms = self.primary_keywords + self.secondary_keywords + self.exclusion_keywords 
        return ", ".join(self.query_terms)
    
    def make_query(self):
        return self.query_terms

    def edit_query_terms(self):
        
        if not st.session_state["keywords_finalized"]:
            with st.form("my_form"):
                st.session_state["primary_keywords"] = st.text_area("Primary Keywords (comma-separated):", ", ".join(self.primary_keywords))
                st.session_state["secondary_keywords"] = st.text_area("Secondary Keywords (comma-separated):", ", ".join(self.secondary_keywords))
                st.session_state["exclusion_keywords"]  = st.text_area("Exclusion Keywords (comma-separated):", ", ".join(self.exclusion_keywords))
                
                keywords_submitted = st.form_submit_button("Looks good!")
                if keywords_submitted:
                    st.session_state['keywords_finalized'] = True                

        if st.session_state['keywords_finalized']:
            self.primary_keywords = [keyword.strip() for keyword in st.session_state["primary_keywords"].split(",")]
            self.secondary_keywords = [keyword.strip() for keyword in st.session_state["secondary_keywords"].split(",")]
            self.exclusion_keywords = [keyword.strip() for keyword in st.session_state["exclusion_keywords"] .split(",")]
            self.query_terms = self.primary_keywords + self.secondary_keywords + self.exclusion_keywords
            print("Keywords finalized")
          

    def get_filename(self):
        return review_config.SR_STEP2_FILENAME
    
    def _write_search_results(self, articles_df, query):

        # Reindex dataframes and Append new results to it
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df.reset_index(drop=True, inplace=True)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        # Remove duplicates based on the 'PMID' column
        articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)

        # Call parent method to write the combined results to excel
        super()._write_search_results(articles_df, query)

