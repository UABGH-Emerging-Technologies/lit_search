from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from typing import Tuple
import datetime
from llm_utils.database import write_to_db
from ScopingReview.compile import FastAPISummarizeManager
from ScopingReview.upload import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config

router = APIRouter(tags=["scoping", "step4"])

async def get_step4_response(background_tasks: BackgroundTasks, research_question: str, file: UploadFile) -> Tuple[str, FileResponse]:
    """
    The function `get_step4_response` processes an uploaded Excel file, summarizes it based on a
    research question, saves the summary to a temporary file, and logs the processing details to a
    database.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is an instance of the
    `BackgroundTasks` class in FastAPI. It allows you to add background tasks to be run after the
    response is returned to the client. In this function, it is used to add a task to write some
    information to a database after processing the
      research_question (str): The `research_question` parameter is a string that represents the
    question or topic related to the research that the user wants to summarize using the uploaded file.
    It is used as input to the summarization process to generate a summary based on the content of the
    file and the specified research question.
      file (UploadFile): The `file` parameter in the `get_step4_response` function is of type
    `UploadFile`. This parameter is used to upload a file, which is expected to be in Excel format
    (`.xlsx`). The function processes the uploaded file to summarize its content based on a research
    question provided.
    
    Returns:
      The function `get_step4_response` returns a tuple containing the temporary file path where the
    summarized data is saved and a `FileResponse` object that represents the summarized data file.
    """
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["xlsx"])
        df, _ = await upload_manager.upload_file(file)
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        summarize_manager = FastAPISummarizeManager(df, research_question)
        temp_file_path, warning_msg = summarize_manager.summarize_and_save()
        if warning_msg:
            headers = {"Warning": warning_msg}
        else:
            headers = {}
        response = FileResponse(
            path=temp_file_path, 
            filename=summarize_manager.get_doc_filename(),
            media_type=summarize_manager.get_mime_type(),
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finish = datetime.datetime.now()
    try:
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"question":"{research_question}"}}',
            start,
            finish,
            summarize_manager.cost,
            "_scoping_step4_summarization"
        )
    except KeyError:
        pass

    return temp_file_path, response

@router.post("/search/v01/scoping/step4/", **lit_api_config.SCOPING_STEP4_META)
async def summarize_articles(background_tasks: BackgroundTasks, research_question: str, file: UploadFile = File(...)) -> FileResponse:
    """
    Receives an uploaded Excel file containing article data and a research question, performs summarization based on the provided research question, and returns a downloadable DOCX file with the summarized content.

    This endpoint is part of a scoping workflow where users need to extract concise summaries from large sets of articles based on specific research queries. It handles the full process: file upload, data processing, summarization, and the creation of a downloadable summary document. Additionally, details of the processing are logged to a database for auditing and tracking purposes.

    Args:
        research_question (str): The research question or topic that guides the summarization process. This string is used to tailor the summarization algorithm to focus on relevant content within the uploaded articles.
        file (UploadFile, optional): The file containing article data. This file should be in Excel format and contain the necessary data for summarization. Defaults to File(...), which is a placeholder indicating that a file must be provided.

    Returns:
        FileResponse: A FastAPI response object that facilitates the direct download of the generated summary. The file is returned as a DOCX document, suitable for review and distribution.

    Raises:
        HTTPException: If the file is not processed correctly, a 422 error is returned with details explaining the issue.
        HTTPException: If any internal errors occur during the processing, a 500 error is returned with a message describing the error.

    Usage:
        The endpoint is designed to be used as part of a scoping step in research where quick summarization of articles is required. It accepts a file upload directly through a client interface, such as a web form.
    """
    temp_file_path, response = await get_step4_response(background_tasks, research_question, file)
    background_tasks.add_task(os.unlink, temp_file_path)
    return response
