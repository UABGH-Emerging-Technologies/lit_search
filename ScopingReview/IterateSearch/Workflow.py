import os
import pandas as pd
from aiweb_common.resource.PubMedInterface import PubMedInterface
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
from Bio import Entrez
from ScopingReview.InitialSearch.Workflow import ArticleSearch
from ScopingReview.IterateSearch.Manager import FastAPIIterateSearchManager
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview_config import app_config, config

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY


class IterateSearch(ArticleSearch):
    def __init__(
        self,
        df: pd.DataFrame,
        research_question: str,
        keywords: KeywordData,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        # Call parent __init__ with all required parameters
        super().__init__(
            research_question=research_question,
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )
        self.openai_compatible_endpoint = openai_compatible_endpoint
        self.openai_compatible_key = openai_compatible_key
        self.openai_compatible_model = openai_compatible_model
        # Pass LLM config to manager
        self.iterate_search_manager = FastAPIIterateSearchManager(
            df,
            research_q=research_question,
            keywords=keywords,
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def process(self):
        print("Refining Query with Keywords")
        refined_query = self.iterate_search_manager.refine_query()
        
        # Create ArticleSearch with LLM parameters
        self.search_workflow = ArticleSearch(
            refined_query,
            self.openai_compatible_endpoint,
            self.openai_compatible_key,
            self.openai_compatible_model,
        )
        articles_df = self.search_workflow.process()
        
        # Ensure 'PMID' columns are strings for merge
        articles_df["PMID"] = articles_df["PMID"].astype(str)
        self.iterate_search_manager.selected_articles_df["PMID"] = (
            self.iterate_search_manager.selected_articles_df["PMID"].astype(str)
        )
        
        # Merge the 'Relevant' column from selected_articles_df if present
        if "Relevant" in self.iterate_search_manager.selected_articles_df.columns:
            articles_df = articles_df.merge(
                self.iterate_search_manager.selected_articles_df[["PMID", "Relevant"]],
                on="PMID",
                how="left"
            )
        else:
            articles_df["Relevant"] = None
        
        return articles_df, refined_query