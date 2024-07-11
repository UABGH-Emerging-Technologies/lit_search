from llm_utils.api_utils.WorkflowHandler import WorkflowHandler
from llm_utils.generate.SingleResponse import SingleResponseHandler
from ScopingReview_config import prompt_config, config
import pandas as pd

class SummarizeWorkflow(WorkflowHandler):
    def __init__(self, df: pd.DataFrame, research_question: str):
        super().__init__()
        self.df = df
        self.research_question = research_question

    def process(self):
        assembled_prompt, single_response = self._assemble_prompt(
            prompt_config.SUMMARIZE_SYSTEM_TEMPLATE,
            prompt_config.SUMMARIZE_HUMAN_TEMPLATE,
            question=self.research_question,
            context=self.df.to_dict()
        )
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return response.content
