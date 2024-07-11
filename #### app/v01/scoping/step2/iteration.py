import base64
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from ScopingReview.workflows import CompileManager
from ScopingReview_config import app_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.scoping.step2.schemas import IterationRequest
from app.v01.schemas import MSExcelResponse
from app.fastapi_config import SCOPING_STEP2EXCEL_META
from llm_utils.file_operations.file_handling import file_to_base64

router = APIRouter(tags=["scoping", "step2"])

def get_step2iteration_response(background_tasks: BackgroundTasks, question: str, xlsx_encoded: str, keywords: KeywordsData) -> MSExcelResponse:
    start = datetime.now()
    try:
        manager = CompileManager(None, question)
        df = manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        categorized_df = manager.categorize(keywords.primary_keywords + keywords.secondary_keywords)
        temp_file_path = manager.save_to_excel(categorized_df)
        encoded_file = file_to_base64(temp_file_path)
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()

    content_to_log = f'{{"question":"{question}"}}'
    manager.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step2")
    
    return response

@router.post("/search/v01/scoping/step2/iteration/", **SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(background_tasks: BackgroundTasks, request: IterationRequest) -> MSExcelResponse:
    keywords = KeywordsData(
        primary_keywords=request.primary_keywords,
        secondary_keywords=request.secondary_keywords,
        exclusion_keywords=request.exclusion_keywords
    )
    return get_step2iteration_response(background_tasks, request.research_question, request.xlsx_encoded, keywords)
