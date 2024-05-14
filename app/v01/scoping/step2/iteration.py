import os
from typing import Tuple
from fastapi import File, UploadFile, APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from datetime import datetime

from llm_utils.database import write_to_db

import ScopingReview_config.app_config as lit_app_config
from ScopingReview.search import FastAPIIterateSearchManager
import app.fastapi_config as lit_api_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.schemas import SearchRequest

# TODO: metadata
router = APIRouter(tags=["scoping", "step2"])

async def get_step2iteration_response(background_tasks: BackgroundTasks, question: str, file: UploadFile, keywords: KeywordsData) -> Tuple[str, FileResponse]:
    start = datetime.now()
    try:
        df = await FastAPIIterateSearchManager.read_excel(file)
        manager = FastAPIIterateSearchManager(df, question)
        temp_file_path = await manager.update_keywords_and_perform_search(keywords)
        response = FileResponse(path=temp_file_path, filename="Updated_Search_Results.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finish = datetime.now()
    
    try:
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}',
            start,
            finish,
            manager.total_cost,  # ensure total_cost is handled after the search
            "_scoping_step2_excel",
        )
    except KeyError:
        pass
    
    return temp_file_path, response

@router.post("/search/v01/scoping/step2/iteration/", **lit_api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(background_tasks: BackgroundTasks, keywords: KeywordsData, query: SearchRequest = Depends(), file: UploadFile = File(...),) -> FileResponse:
    temp_file_path, response = await get_step2iteration_response(query.research_question, file, keywords)
    background_tasks.add_task(os.unlink, temp_file_path)
    return response
