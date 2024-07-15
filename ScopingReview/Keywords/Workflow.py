from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from ScopingReview.Keywords.Manager import KeywordManager
from ScopingReview_config import config, prompt_config

class KeywordWorkflow(WorkflowHandler):
    def __init__(self, df, research_question):
        super().__init__()
        self.df = df
        self.research_question = research_question
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)
        self.keyword_manager = KeywordManager(self.df, self.research_question)

    def generate_keywords(self):
        relevant_rows = self.keyword_manager.get_relevant_rows()
        all_titles = relevant_rows['title'].tolist()
        formatted_keywords = self.keyword_manager.format_keywords(relevant_rows)
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.GENERATE_SYSTEM_KEYWORD_PROMPT, 
            user_prompt = prompt_config.GENERATE_HUMAN_KEYWORD_PROMPT, 
            question = self.research_question,
            titles = all_titles,
            keywords_list = formatted_keywords
        )
        
        response, response_meta = self.single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return response.content

    def initialize_keywords(self, primary, secondary, exclusion):
        query_terms = primary + secondary

        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.GENERATE_SYSTEM_KEYWORD_PROMPT, 
            user_prompt = prompt_config.GENERATE_HUMAN_KEYWORD_PROMPT, 
            question = self.research_question,
            keywords_list = query_terms
        )
        result, response_meta = self.single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return result
    
    def process(self):
        generated_keywords_json = self.generate_keywords()
        primary, secondary, exclusion = self.keyword_manager.parse_keywords(str(generated_keywords_json))
        result = self.initialize_keywords(primary, secondary, exclusion)
        return result
