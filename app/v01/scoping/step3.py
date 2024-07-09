from fastapi import APIRouter, HTTPException, BackgroundTasks

import datetime
from aiweb_common.database import write_to_db
from ScopingReview.CompileManager import FastAPICategorizeManager
from ScopingReview.UploadManager import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.schemas import CategoriesRequest
from llm_utils import api_utils

router = APIRouter(tags=["scoping", "step3"])

def get_step3_response(background_tasks: BackgroundTasks,
                             user_defined_categories: str,
                             xlsx_encoded: str) -> MSExcelResponse:
    """
    This function reads and validates an Excel file, categorizes articles based on user-defined
    categories, saves the categorized data to a temporary file, converts the file to a base64 string,
    and then returns a response with the encoded file.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is an object that allows you
    to add background tasks to be run after sending the response to the client. These tasks are
    typically non-blocking and can be used for operations like cleaning up temporary files, sending
    emails, or updating databases asynchronously. In the provided function `get_step
      user_defined_categories (str): The `user_defined_categories` parameter in the `get_step3_response`
    function is a string that represents the categories defined by the user for categorizing articles in
    the Excel file. These categories are used by the `FastAPICategorizeManager` to categorize the
    articles and save the results in
      xlsx_encoded (str): The `xlsx_encoded` parameter in the `get_step3_response` function is a string
    that represents the Excel file encoded in base64 format. This function reads and validates the Excel
    file, categorizes the articles based on user-defined categories, saves the categorized articles to a
    temporary file, converts the temporary
    
    Returns:
      The function `get_step3_response` returns an instance of `MSExcelResponse`.
    """
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager()
        df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        manager = FastAPICategorizeManager(df, user_defined_categories)
        temp_file_path = manager.categorize_articles_and_save()
        encoded_file = api_utils.file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.datetime.now()
    try:
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"categories":"{user_defined_categories}"}}',
            start,
            finish,
            manager.cost,
            "_scoping_step3_categorization"
        )
    except KeyError:
        pass

    return response

@router.post("/search/v01/scoping/step3/", **lit_api_config.SCOPING_STEP3_META)
async def categorize_articles(
    background_tasks: BackgroundTasks,
    request: CategoriesRequest
    ) -> MSExcelResponse:
    """
    Processes an uploaded Excel file to categorize articles based on user-defined categories, then returns a downloadable Excel file with the results.

    This endpoint takes a byte-encoded Excel file containing article data and a string of user-defined categories to perform categorization. After processing, it generates a new Excel file with articles organized into the specified categories, which can be directly downloaded.
    """
    response = get_step3_response(
        background_tasks,
        request.user_defined_categories,
        request.xlsx_encoded
        )

    return response
