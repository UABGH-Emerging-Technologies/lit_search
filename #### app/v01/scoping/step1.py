from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from ScopingReview.workflows import SearchWorkflow
from ScopingReview_config import app_config
from app.v01.schemas import SearchRequest, MSExcelResponse
from app.fastapi_config import SCOPING_STEP1_META
from llm_utils.file_operations.file_handling import file_to_base64
import os  # Importing the os module

router = APIRouter(tags=["scoping", "step1"])

def get_step1_response(background_tasks: BackgroundTasks, research_question: str) -> MSExcelResponse:
    start = datetime.now()
    try:
        workflow = SearchWorkflow(research_question)
        search_results = workflow.process()
        
        temp_file_path = workflow.save_to_excel(search_results)
        encoded_file = file_to_base64(temp_file_path)
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()

    content_to_log = f'{{"query":"{research_question}"}}'
    workflow.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step1")
    
    return response

@router.post("/search/v01/scoping/step1/", **SCOPING_STEP1_META)
async def perform_step1_scoping_search(background_tasks: BackgroundTasks, query: SearchRequest) -> MSExcelResponse:
    return get_step1_response(background_tasks, query.research_question)
