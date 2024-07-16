import os
from ScopingReview.InitialSearch.Workflow import ArticleSearch
from ScopingReview_config import config, app_config
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
from aiweb_common.resource.PubMedInterface import PubMedInterface

from Bio import Entrez

from ScopingReview.IterateSearch.Manager import FastAPIIterateSearchManager

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY

class IterateSearch(ArticleSearch):
    def __init__(self, df, research_question):
        super().__init__(research_question=research_question)
        self.search_manager = FastAPIIterateSearchManager(df, research_q=research_question)
        self.query_generator = PubMedQueryGenerator(config.LLM_INTERFACE, self.research_question)
        self.pubmed_interface = PubMedInterface()
        
    def process(self):
        initial_query = self.search_manager.manage_keyword_extraction()
        search_string = self.query_generator.generate_search_string(initial_query)
        articles_df = self.pubmed_interface.search_pubmed_articles(search_string)
        self.search_manager.update_articles(articles_df)
        return articles_df
