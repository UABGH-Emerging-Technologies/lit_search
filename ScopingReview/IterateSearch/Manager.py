import pandas as pd
from fastapi import HTTPException

from ScopingReview.InitialSearch.Manager import BaseSearchManager
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from ScopingReview_config import config 
import tempfile

# This class `BaseIterateSearchManager` extends `BaseSearchManager` and includes methods for preparing
# a query with keywords, determining keywords, refining the query, and updating articles in a
# DataFrame.
class BaseIterateSearchManager(BaseSearchManager):
    def __init__(self, df, research_q, keywords):
        super().__init__(None, research_q)
        self.df = df
        self.selected_articles_df = self.get_relevant_rows()
        self.query_terms = []
        self.primary_keywords = keywords.primary_keywords
        self.secondary_keywords = keywords.secondary_keywords
        self.exclusion_keywords = keywords.exclusion_keywords
        self.keyword_workflow = KeywordWorkflow(self.df, research_question=research_q)
        
    def _get_filename(self):
        return config.SR_STEP2_FILENAME
    
    def _get_mime_type(self):
        return config.EXCEL_MIME
    
    def _prepare_query_with_keywords(self):
        self.query_prompt = (
                "Overall Research Question: " + self.research_q +
                "\n\n Primary topics to include in query: " + ", ".join(self.primary_keywords) +
                ". Secondary topics to include in query: " + ", ".join(self.secondary_keywords) +
                ". Here's a set of topics to exclude in query construction: " + ", ".join(self.exclusion_keywords)
            )
        print(self.query_prompt)
        return self.query_prompt
    
    def determine_keywords(self):
        generated_keywords = self.keyword_workflow.process()
        self.primary_keywords, self.secondary_keywords, self.exclusion_keywords = generated_keywords
        return generated_keywords

    def refine_query(self):
        return self._prepare_query_with_keywords()

    def update_articles(self, articles_df):
        self.selected_articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        self.selected_articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)
           
class FastAPIIterateSearchManager(BaseIterateSearchManager):
    def __init__(self, df: pd.DataFrame, research_q: str, keywords: KeywordData):
        super().__init__(df, research_q, keywords)
        

