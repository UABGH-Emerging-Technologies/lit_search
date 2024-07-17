from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from ScopingReview_config import app_config
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
import app.fastapi_config as api_config
from ScopingReview.Keywords.Manager import KeywordData
from app.v01.scoping.step2.schemas import KeywordsRequest

router = APIRouter(tags=["scoping", "step2"])

def get_step2keywords_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str
    ) -> KeywordData:
    """
    This function takes in a question and an encoded Excel file, processes the file to extract keywords
    related to the question, logs the keywords to a database, and returns the extracted keywords.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is used to handle background
    tasks in FastAPI. It allows you to perform tasks asynchronously without blocking the main
    application flow. These tasks can include things like sending emails, processing data in the
    background, or any other task that doesn't need an immediate response.
      question (str): The `question` parameter in the `get_step2keywords_response` function is a string
    that represents the question for which you want to extract keywords from the provided Excel file.
    This question will be used in the keyword extraction process along with the data from the Excel file
    to generate relevant keywords.
      xlsx_encoded (str): The `xlsx_encoded` parameter in the `get_step2keywords_response` function is a
    string that represents the encoded content of an Excel file. This encoded content is typically used
    for uploading and processing Excel files in web applications. The function reads and validates the
    Excel file content using the `FastAPIUpload
    
    Returns:
      The function `get_step2keywords_response` is returning the keywords extracted from the provided
    question and Excel file after processing them through a keyword workflow.
    """
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df =  upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        keyword_workflow = KeywordWorkflow(df, question)
        print("Processing dataframe")
        keywords = keyword_workflow.process()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    try:
        print("Preparing content to lo log")
        content_to_log = f'{{"Keywords":"{keywords}"}}'
        keyword_workflow.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step2_keywords")
        print('Content logged')
    except KeyError:
        pass
    return keywords

@router.post("/search/v01/scoping/step2/keywords/", **api_config.SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(
    background_tasks: BackgroundTasks,
    request: KeywordsRequest
    ) -> KeywordData:
    """
    This Python function `suggest_keywords` takes in a research question and an encoded Excel file,
    processes the data using `get_step2keywords_response` function, and returns the resulting keywords.
    
    Args:
      background_tasks (BackgroundTasks): BackgroundTasks is a class provided by FastAPI that allows you
    to add background tasks to be run after returning a response to the client. It is typically used for
    tasks that are not critical for the response and can be run asynchronously.
      request (KeywordsRequest): The `request` parameter in the `suggest_keywords` function is of type
    `KeywordsRequest`. It contains information such as the research question and an encoded Excel file.
    
    Returns:
      The function `suggest_keywords` is returning a `KeywordData` object, which is the result of
    calling the `get_step2keywords_response` function with the provided parameters.
    """
    keywords = get_step2keywords_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded
        )
    return keywords
