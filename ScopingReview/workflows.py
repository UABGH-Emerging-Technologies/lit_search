
from llm_utils.api_utils.WorkflowHandler import WorkflowHandler
from llm_utils.SingleResponse import SingleResponseHandler
from ScopingReview_config import config, prompt_config

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question
        
    def process(self):
        #Gather references from pubmed
        
        
        single_response = SingleResponseHandler(config.LLM_INTERFACE)
               
        print('assembling prompts')
        assembled_prompt = single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SIMPLIFY_SYSTEM_TEMPLATE, 
            user_prompt = prompt_config.SIMPLIFY_HUMAN_TEMPLATE, 
            text = self.query
        )