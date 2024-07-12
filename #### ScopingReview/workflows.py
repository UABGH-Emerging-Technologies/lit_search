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
from ScopingReview.SearchWorkflow import ArticleSearch
from ScopingReview.CategorizeWorkflow import CategorizeWorkflow

class CompileManager:
    def __init__(self, df: pd.DataFrame, research_question: str):
        self.df = df
        self.research_question = research_question
        self.cost = 0

    def search(self):
        search_workflow = ArticleSearch(research_question=self.research_question)
        search_results = search_workflow.process()
        self.cost += search_workflow.total_cost
        return search_results
        
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
