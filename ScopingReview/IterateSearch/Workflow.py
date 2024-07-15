import os
from ScopingReview.InitialSearch.Workflow import ArticleSearch
from ScopingReview_config import config, app_config
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator

from Bio import Entrez

from ScopingReview.IterateSearch.Manager import FastAPIIterateSearchManager

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY

class IterateSearch(ArticleSearch):
    def __init__(self, df, research_question):
        super().__init__(research_question=research_question)
        self.search_manager = FastAPIIterateSearchManager(df, research_q=research_question)
        query_generator = PubMedQueryGenerator(config.LLM_INTERFACE, self.research_question)
        
    #TODO Rewrite this to not just be the initial search
    def process(self):

        self.search_manager.initialize_keywords
        
        
        
        
        

                    
        

