from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
import datetime
from ScopingReview.Summarize.Workflow import SummarizeArticles
from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import SummariesRequest
from aiweb_common.file_operations.file_handling import file_to_base64

router = APIRouter(tags=["scoping", "step4"])

def get_step4_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    xlsx_encoded: str,
    ) -> MSWordResponse:
    """
    This function takes a research question and an encoded Excel file, processes the file, summarizes
    the data based on the research question, saves the summary as a Word document, and logs the process
    in a database.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter in the `get_step4_response`
    function is used to handle background tasks in FastAPI. These tasks are executed asynchronously and
    are commonly used for operations like file processing, sending emails, or making external API calls
    without blocking the main application flow. In this function, the
      research_question (str): The `research_question` parameter in the `get_step4_response` function is
    a string that represents the question or topic for which the user wants to summarize data from the
    uploaded Excel file. This question guides the summarization process and helps in generating a
    concise summary based on the data in the Excel file
      xlsx_encoded (str): The `xlsx_encoded` parameter in the `get_step4_response` function is a string
    that represents the content of an Excel file encoded in base64 format. This function reads and
    validates the Excel file, summarizes its content based on a research question, saves the summary to
    a temporary file, converts the
    
    Returns:
      The function `get_step4_response` returns a tuple containing two elements: 
    1. The `MSWordResponse` object named `response` which includes the encoded Word document.
    2. The `warning_msg` variable which may contain any warning message generated during the processing
    of the file.
    """
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        summarization = SummarizeArticles(df, research_question)
        # TODO: have process() return md string
        temp_file_path, warning_msg = summarization.process()
        # add method to return temp_file_path
        encoded_file = file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.datetime.now()
    try:
        # Adding a background task to write search details to the database
        content_to_log = f'{{"query":"{research_question}"}}'
        summarization.log_to_database(lit_app_config, content_to_log, start, finish, background_tasks, label="_scoping_step4")
    except KeyError:
        pass

    return response, warning_msg

@router.post("/search/v01/scoping/step4/", **lit_api_config.SCOPING_STEP4_META)
async def summarize_articles(
    background_tasks: BackgroundTasks,
    request: SummariesRequest,
    response: Response
    ) -> MSWordResponse:
    """
    Receives an uploaded Excel file containing article data and a research question, performs summarization based on the provided research question, and returns a downloadable DOCX file with the summarized content.

    This endpoint is part of a scoping workflow where users need to extract concise summaries from large sets of articles based on specific research queries. It handles the full process: file upload, data processing, summarization, and the creation of a downloadable summary document. Additionally, details of the processing are logged to a database for auditing and tracking purposes.
    """
    response_data, warning_message = get_step4_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded)
    # Optionally add a warning
    if warning_message:
        response.headers["Warning"] = warning_message
    return response_data
