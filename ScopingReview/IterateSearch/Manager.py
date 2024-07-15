from ScopingReview.InitialSearch.Manager import BaseSearchManager
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from ScopingReview_config import config 
import pandas as pd
from fastapi import HTTPException
import tempfile

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
        self.keyword_workflow = KeywordWorkflow(self.df, research_question=research_q)
        
    def _get_filename(self):
        return config.SR_STEP2_FILENAME
    
    def _get_mime_type(self):
        return config.EXCEL_MIME

    def determine_keywords(self):
        generated_keywords = self.keyword_workflow.process()
        self.primary_keywords, self.secondary_keywords, self.exclusion_keywords = generated_keywords
        return generated_keywords

    def perform_search(self, search_string):
        self.selected_articles_df.reset_index(drop=True, inplace=True)
        articles_df = super().perform_search(search_string)
        articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)
        return articles_df

    def manage_keyword_extraction(self):
        if not self.keywords_extracted:
            generated_keywords = self.determine_keywords()
            self.keywords_extracted = True
        return generated_keywords

    def update_articles(self, articles_df):
        self.selected_articles_df = pd.concat([self.selected_articles_df, articles_df], ignore_index=True)
        self.selected_articles_df.drop_duplicates(subset='PMID', keep='first', inplace=True)
           
class FastAPIIterateSearchManager(BaseIterateSearchManager):
    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)
        
    def extract_and_return_keywords(self) -> KeywordData:
        try:
            generated_keywords = self.manage_keyword_extraction() 
            return KeywordData(
                primary_keywords=self.primary_keywords,
                secondary_keywords=self.secondary_keywords,
                exclusion_keywords=self.exclusion_keywords
            )
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
