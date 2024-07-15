from ScopingReview.InitialSearch.Manager import BaseSearchManager
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview_config import config 
import pandas as pd
import streamlit as st

class BaseIterateSearchManager(BaseSearchManager):
    def __init__(self, df, research_q):
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = self.get_relevant_rows()
        self.query_terms = []
        self.primary_keywords = []
        self.secondary_keywords = []
        self.exclusion_keywords = []
        self.keywords_extracted = False
        
    def get_filename(self):
        return config.SR_STEP2_FILENAME

    def determine_keywords(self):
        generated_keywords_json, response_meta = self.keywords_workflow.process()
        (
            self.primary_keywords,
            self.secondary_keywords,
            self.exclusion_keywords,
        ) = self.keywords_workflow.parse_keywords(str(generated_keywords_json))
        self.initialize_keywords(self.primary_keywords, self.secondary_keywords, self.exclusion_keywords)
        return ", ".join(self.query_terms), response_meta.total_cost

    def make_query(self):
        return self.query_terms

    def perform_search(self, search_string):
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df = super().perform_search(search_string)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)
        return articles_df

    def manage_keyword_extraction(self):
        if not self.keywords_extracted:
            initial_query, cost = self.make_initial_query()
            self.keywords_extracted = True
        return initial_query

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

    #TODO This should go away
    def make_initial_query(self):
        with st.spinner("Extracting and grouping keywords from uploaded file"):
            initial_query = super().make_initial_query()
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
            
            print("Keywords finalized session state = ", st.session_state)
            
class FastAPIIterateSearchManager(BaseIterateSearchManager):
    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)
        
    def extract_and_return_keywords(self) -> KeywordData:
        try:
            initial_query = self.manage_keyword_extraction() 
            return KeywordData(
                primary_keywords=self.primary_keywords,
                secondary_keywords=self.secondary_keywords,
                exclusion_keywords=self.exclusion_keywords
            ),
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


    def update_keywords_and_perform_search(self, keywords: KeywordData) -> str:
        try:
            self.initialize_keywords(keywords.primary_keywords, keywords.secondary_keywords, keywords.exclusion_keywords)
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
