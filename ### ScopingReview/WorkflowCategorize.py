from llm_utils.api_utils.WorkflowHandler import WorkflowHandler
from llm_utils.generate.SingleResponse import SingleResponseHandler
from ScopingReview_config import prompt_config, config
import pandas as pd
from typing import List

class CategorizeWorkflow(WorkflowHandler):
    def __init__(self, df: pd.DataFrame, categories: List[str]):
        super().__init__()
        self.df = df
        self.categories = categories

    def process(self):
        assembled_prompt, single_response = self._assemble_prompt(
            prompt_config.CATEGORIZE_SYSTEM_TEMPLATE,
            prompt_config.CATEGORIZE_HUMAN_TEMPLATE,
            categories=self.categories,
            context=self.df.to_dict()
        )
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return response.content
