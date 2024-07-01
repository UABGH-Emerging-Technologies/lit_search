from llm_utils.api_utils.WorkflowHandler import WorkflowHandler
from llm_utils.SingleResponse import SingleResponseHandler
from ScopingReview_config import config, prompt_config
import ScopingReview.data as review_data

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question

    def process(self):
        # Gather references from PubMed
        single_response = SingleResponseHandler(config.LLM_INTERFACE)
        
        print('Assembling prompts')
        assembled_prompt = single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.SIMPLIFY_SYSTEM_TEMPLATE,
            user_prompt=prompt_config.SIMPLIFY_HUMAN_TEMPLATE,
            text=self.research_question
        )
        
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        
        return response.content

    def search_and_compile(self):
        query = self.research_question
        pm_connection, article_ids = review_data.search_and_compile(query)
        articles_df = review_data.make_initial_df(pm_connection, article_ids)
        return articles_df

    def write_excel_output(self, tmpfile, df, input_search_terms, query_strings=""):
        review_data.write_excel_output(tmpfile, df, input_search_terms, query_strings)
