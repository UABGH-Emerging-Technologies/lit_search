from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
import datetime
from llm_utils.database import write_to_db
from ScopingReview.compile import FastAPICategorizeManager
from ScopingReview.upload import FastAPIUploadManager
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
    This asynchronous Python function processes an uploaded file by categorizing its contents based on
    user-defined categories and saves the categorized articles, while also logging relevant information
    to a database using background tasks.
    
    Args:
      background_tasks (BackgroundTasks): `BackgroundTasks` is a class provided by FastAPI that allows
    you to add background tasks to be run after returning a response to the client. In this function, it
    is used to add a task to write data to a database after processing the file.
      user_defined_categories (str): The `user_defined_categories` parameter is a string that contains
    user-defined categories separated by commas. These categories are used to categorize the articles in
    the uploaded file.
      file (UploadFile): The `file` parameter in the `get_step3_response` function is of type
    `UploadFile`. It is used to receive an uploaded file from the client. In this case, the function is
    expecting an Excel file (with extension .xlsx) to be uploaded by the user. The uploaded file
    
    Returns:
      The function `get_step3_response` returns the `file_path` variable, which is the path where the
    categorized articles are saved after processing the uploaded file and categorizing them based on the
    user-defined categories.
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

    This endpoint takes an Excel file containing article data and a string of user-defined categories to perform categorization. After processing, it generates a new Excel file with articles organized into the specified categories, which can be directly downloaded.

    Args:
        user_defined_categories (str): A comma-separated string of categories specified by the user under which the articles will be organized.
        file (UploadFile, optional): The Excel file uploaded by the user containing articles to be categorized. Defaults to File(...).

    Returns:
        FileResponse: A FastAPI response object that enables direct downloading of the categorized Excel file. The file is named 'Categorized_Articles.xlsx' and has the MIME type for Excel files.

    Raises:
        HTTPException: Returns a 422 error if the file could not be processed or if the file is missing necessary data.
        HTTPException: Returns a 500 error for any internal server errors during processing, such as failure in reading the file or issues during the categorization process.

    The endpoint also logs the operation details to a database as a background task, including the start and finish times and the cost of the categorization process, enhancing traceability and auditability.
    """
    response = get_step3_response(
        background_tasks,
        request.user_defined_categories,
        request.xlsx_encoded
        )

    return response
