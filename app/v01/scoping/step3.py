from fastapi import APIRouter, HTTPException, BackgroundTasks

import datetime
from ScopingReview.Categorize.Workflow import CategorizeWorkflow
from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
from ScopingReview_config import app_config
import os
import app.fastapi_config as api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.schemas import CategoriesRequest
from aiweb_common.file_operations.file_handling import file_to_base64

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
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        categorize_workflow = CategorizeWorkflow(df, user_defined_categories)
        #TODO convert to match other processes (process returns df, call write_excel_file...)
        category_df = categorize_workflow.process()

        encoded_file = categorize_workflow.manager.get_encoded_excel(
            category_df, 
            background_tasks=background_tasks,
            research_question=user_defined_categories
            )

        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.datetime.now()
    try:
        pass
        content_to_log = f'{{"User Defined Categories":"{user_defined_categories}"}}'
        categorize_workflow.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step3_categorize")
    except KeyError:
        pass

    return response

@router.post("/search/v01/scoping/step3/", **api_config.SCOPING_STEP3_META)
async def categorize_articles(
    background_tasks: BackgroundTasks,
    request: CategoriesRequest
    ) -> MSExcelResponse:
    """
    This endpoint categorizes articles from an input Excel file based on user-defined categories, then returns a downloadable Excel file with the sorted articles.
    """
    response = get_step3_response(
        background_tasks,
        request.user_defined_categories,
        request.xlsx_encoded
        )

    return response
