from llm_utils.api_utils.WorkflowHandler import WorkflowHandler
from llm_utils.generate.SingleResponse import SingleResponseHandler
import ScopingReview_config.boilerplate as lit_boilerplate
from ScopingReview_config import prompt_config, config
import pandas as pd
from typing import List, Tuple, Union
from fastapi import HTTPException
import tempfile
import os
from io import BytesIO
import pypandoc
import base64

class BaseWorkflow(WorkflowHandler):
    def __init__(self, research_question: str):
        super().__init__()
        self.research_question = research_question

    def _assemble_prompt(self, system_prompt, user_prompt, **kwargs):
        single_response = SingleResponseHandler(config.LLM_INTERFACE)
        assembled_prompt = single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **kwargs
        )
        return assembled_prompt, single_response

class SearchWorkflow(BaseWorkflow):
    def __init__(self, research_question: str):
        super().__init__(research_question)

    def process(self):
        assembled_prompt, single_response = self._assemble_prompt(
            prompt_config.SEARCH_SYSTEM_TEMPLATE,
            prompt_config.SEARCH_HUMAN_TEMPLATE,
            question=self.research_question
        )
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        return response.content

class CategorizeWorkflow(BaseWorkflow):
    def __init__(self, df: pd.DataFrame, categories: List[str]):
        super().__init__(None)
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

class SummarizeWorkflow(BaseWorkflow):
    def __init__(self, df: pd.DataFrame, research_question: str):
        super().__init__(research_question)
        self.df = df

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

class CompileManager:
    def __init__(self, df: pd.DataFrame, research_question: str):
        self.df = df
        self.research_question = research_question
        self.cost = 0

    def categorize(self, categories: List[str]) -> pd.DataFrame:
        workflow = CategorizeWorkflow(self.df, categories)
        categorized_content = workflow.process()
        self.cost += workflow.total_cost
        return pd.DataFrame(categorized_content)

    def summarize(self) -> str:
        workflow = SummarizeWorkflow(self.df, self.research_question)
        summarized_content = workflow.process()
        self.cost += workflow.total_cost
        return summarized_content

    def save_to_excel(self, df: pd.DataFrame) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            df.to_excel(tmpfile.name, index=False)
            return tmpfile.name

    def save_to_docx(self, content: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
            pypandoc.convert_text(content, 'docx', format='md', outputfile=tmpfile.name)
            return tmpfile.name

    def read_file(self, file: bytes, extension: str) -> Union[pd.DataFrame, str]:
        if extension == ".xlsx":
            return pd.read_excel(BytesIO(file))
        elif extension == ".docx":
            with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmpfile:
                tmpfile.write(file)
                tmpfile.seek(0)
                return pypandoc.convert_file(tmpfile.name, "markdown")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file extension: {extension}")

    def read_and_validate_file(self, encoded_file: str, extension: str) -> Union[pd.DataFrame, str]:
        try:
            file_bytes = base64.b64decode(encoded_file)
            output = self.read_file(file_bytes, extension)
            if output is None:
                raise HTTPException(status_code=422, detail="Failed to process the file")
            return output
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
