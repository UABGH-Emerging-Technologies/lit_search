import os
from aiweb_common.WorkflowHandler import WorkflowHandler
from ScopingReview_config import config, app_config
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator

from Bio import Entrez

from ScopingReview.InitialSearch.Manager import FastAPISearchManager

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question
        self.search_manager = FastAPISearchManager(scoping_step=None, research_q=research_question)
        
    def write_excel_output(self, temp_file_path, articles_df, research_question):   
        self.search_manager.write_search_excel_output(tmpfile=temp_file_path, df=articles_df, input_search_terms=research_question)

    def process(self):
        query_generator = PubMedQueryGenerator(config.LLM_INTERFACE, self.research_question)
        n=0
        search_string=""
        print('Generating PubMed Queries')

        while n <= config.MAX_TRIES:
            search_string = query_generator.generate_search_string(loop_n=n, last_query = search_string)
            print("QUERY - ", search_string)
            article_ids = self.search_manager.pubmed_interface.search_pubmed_articles(search_string)
            print('Number of articles found - ', len(article_ids))
            if len(article_ids)>config.MIN_ARTICLES:
                articles_df = self.search_manager.pubmed_interface.fetch_article_details(article_ids)
                return articles_df
            else:
                n=n+1
        
        print("Insufficient number of articles found in {config.MAX_TRIES} tries")
        return None
                    
        

