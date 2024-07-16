from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from ScopingReview.Keywords.Manager import KeywordManager, KeywordData
from ScopingReview_config import config, prompt_config

class KeywordWorkflow(WorkflowHandler):
    def __init__(self, df, research_question):
        super().__init__()
        self.df = df
        self.research_question = research_question
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)
        self.keyword_manager = KeywordManager(self.df, self.research_question)

    def initialize_keywords(self):
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
        #print("Assembled prompt - ", assembled_prompt)
        response, response_meta = self.single_response.generate_response(assembled_prompt)
        print('Response - ', response)
        self._update_total_cost(response_meta)
        return response.content

    def refine_keywords(self, primary, secondary, exclusion):
        query_terms = primary + secondary
        relevant_rows = self.keyword_manager.get_relevant_rows()
        all_titles = relevant_rows['title'].tolist()
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.GENERATE_SYSTEM_KEYWORD_PROMPT, 
            user_prompt = prompt_config.GENERATE_HUMAN_KEYWORD_PROMPT, 
            question = self.research_question,
            titles = all_titles,
            keywords_list = query_terms
        )
        result, response_meta = self.single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return result.content
    
    def process(self):
        print('Generating Keywords')
        generated_keywords_json = self.initialize_keywords()
        primary, secondary, exclusion = self.keyword_manager.parse_keywords(str(generated_keywords_json))
        keywords = KeywordData(primary_keywords = primary,\
                                secondary_keywords = secondary,\
                                exclusion_keywords = exclusion\
                                )
        return keywords
