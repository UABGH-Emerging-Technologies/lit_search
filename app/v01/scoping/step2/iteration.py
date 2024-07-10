import base64
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks

from datetime import datetime


import ScopingReview_config.app_config as lit_app_config
from ScopingReview.SearchManager import FastAPIIterateSearchManager
from ScopingReview.UploadManager import FastAPIUploadManager
import app.fastapi_config as lit_api_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.scoping.step2.validators import validate_keywords_data
from app.v01.scoping.step2.schemas import IterationRequest
from app.v01.schemas import MSExcelResponse
from aiweb_common.file_operations.file_handling import file_to_base64

# TODO: metadata
router = APIRouter(tags=["scoping", "step2"])

def get_step2iteration_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str,
    keywords: KeywordsData
    ) -> MSExcelResponse:
    """
    This function processes an uploaded Excel file, performs a search based on a question and keywords,
    and returns the search results in an encoded Excel file while also writing relevant data to a
    database.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is used to handle background
    tasks in FastAPI. It allows you to perform tasks asynchronously, such as file processing or database
    operations, without blocking the main request-response cycle. In the provided function
    `get_step2iteration_response`, the `background_tasks` parameter is an instance
      question (str): The `question` parameter in the `get_step2iteration_response` function is a string
    that represents the question or query for which you want to perform a search or analysis on the data
    provided in the uploaded Excel file. It is used by the `FastAPIIterateSearchManager` to perform the
      xlsx_encoded (str): The `xlsx_encoded` parameter in the `get_step2iteration_response` function is
    a string that represents the encoded content of an Excel file. This encoded content is typically
    used for uploading and processing Excel files within the function.
      keywords (KeywordsData): The `keywords` parameter in the `get_step2iteration_response` function is
    of type `KeywordsData`. It likely contains information related to keywords used for searching or
    filtering data.
    
    Returns:
      The function `get_step2iteration_response` returns an instance of `MSExcelResponse`, which
    contains an encoded Excel file (`encoded_xlsx`).
    """
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager()
        df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        # TODO: standardize whether manager returns cost or just has it as an attribute
        manager = FastAPIIterateSearchManager(df, question)
        temp_file_path = manager.update_keywords_and_perform_search(keywords)
        # TODO: Next three lines generalized to something in llm_utils?
        encoded_file = file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    
    try:
      pass
        # TODO - make sure this is adapted to workflows
        # background_tasks.add_task(
        #     write_to_db,
        #     lit_app_config,
        #     f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}',
        #     start,
        #     finish,
        #     manager.total_cost,  # ensure total_cost is handled after the search
        #     "_scoping_step2_excel",
        # )
    except KeyError:
        pass
    
    return response

@router.post("/search/v01/scoping/step2/iteration/", **lit_api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(
    background_tasks: BackgroundTasks,
    request: IterationRequest,
) -> MSExcelResponse:
    """
    Updates keywords and performs a search based on the provided data in an
    asynchronous manner.
    """

    keywords = validate_keywords_data(
        request.primary_keywords,
        request.secondary_keywords,
        request.exclusion_keywords
        )

    response = get_step2iteration_response(background_tasks,
                                           request.research_question,
                                           request.xlsx_encoded,
                                           keywords)
    return response
