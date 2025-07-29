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
    def __init__(self, df: pd.DataFrame, research_question: str, keywords: KeywordData):
        super().__init__(research_question=research_question)
        self.iterate_search_manager = FastAPIIterateSearchManager(
            df, research_q=research_question, keywords=keywords
        )

    def process(self):
        print("Refining Query with Keywords")
        refined_query = self.iterate_search_manager.refine_query()
        self.search_workflow = ArticleSearch(refined_query)
        articles_df = self.search_workflow.process()
        return articles_df, refined_query
