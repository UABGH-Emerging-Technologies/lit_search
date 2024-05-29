import base64
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks

from datetime import datetime

from llm_utils.database import write_to_db

import ScopingReview_config.app_config as lit_app_config
from ScopingReview.search import FastAPIIterateSearchManager
from ScopingReview.upload import FastAPIUploadManager
import app.fastapi_config as lit_api_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.scoping.step2.validators import validate_keywords_data
from app.v01.scoping.step2.schemas import IterationRequest
from app.v01.schemas import MSExcelResponse
from llm_utils import api_utils

# TODO: metadata
router = APIRouter(tags=["scoping", "step2"])

def get_step2iteration_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_bytes: bytes,
    keywords: KeywordsData
    ) -> MSExcelResponse:
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["xlsx"])
        df = upload_manager.read_file(xlsx_bytes, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        # TODO: standardize whether manager returns cost or just has it as an attribute
        manager = FastAPIIterateSearchManager(df, question)
        temp_file_path = manager.update_keywords_and_perform_search(keywords)
        encoded_file = api_utils.file_to_base64(temp_file_path)
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
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
    
    return response

@router.post("/search/v01/scoping/step2/iteration/", **lit_api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(
    background_tasks: BackgroundTasks,
    request: IterationRequest,
) -> MSExcelResponse:

    keywords = validate_keywords_data(
        request.primary_keywords,
        request.secondary_keywords,
        request.exclusion_keywords
        )

    file_bytes = base64.b64decode(request.xlsx_encoded)
    response = get_step2iteration_response(background_tasks,
                                           request.research_question,
                                           file_bytes,
                                           keywords)
    return response
