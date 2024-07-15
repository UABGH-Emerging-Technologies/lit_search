import os
from aiweb_common.WorkflowHandler import WorkflowHandler
from ScopingReview_config import config, app_config
from aiweb_common.resource.PubMedInterface import PubMedInterface
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator

from Bio import Entrez

from ScopingReview.Search.Manager import ArticleSearchManager

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question
        self.search_manager = ArticleSearchManager(scoping_step=None, research_q=research_question)

    def process(self):
        query_generator = PubMedQueryGenerator(config.LLM_INTERFACE, self.research_question)
        pubmed_interface = PubMedInterface()
        n=0
        while n <= config.MAX_TRIES:
            print('Generating PubMed Query')
            search_string = query_generator.generate_search_string()
            print("QUERY - ", search_string)
            article_ids = pubmed_interface.search_pubmed_articles(search_string)
            if len(article_ids>config.MIN_ARTICLES):
                articles_df = pubmed_interface.fetch_article_details(article_ids)
            else:
                n=n+1
                    
        articles_df = self.search_manager.search_and_compile_articles()
        return articles_df
    
class IterateSearch(WorkflowHandler):
    #TODO implement
    pass
