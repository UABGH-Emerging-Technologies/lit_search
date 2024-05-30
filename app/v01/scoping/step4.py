from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
import datetime
from llm_utils.database import write_to_db
from ScopingReview.compile import FastAPISummarizeManager
from ScopingReview.upload import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import SummariesRequest
from llm_utils import api_utils

router = APIRouter(tags=["scoping", "step4"])

def get_step4_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    xlsx_encoded: str,
    ) -> MSWordResponse:

    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager()
        df = upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        summarize_manager = FastAPISummarizeManager(df, research_question)
        temp_file_path, warning_msg = summarize_manager.summarize_and_save()
        encoded_file = api_utils.file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSWordResponse(encoded_docx=encoded_file)
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
    response_data, warning_message = get_step4_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded)
    # Optionally add a warning
    if warning_message:
        response.headers["Warning"] = warning_message
    return response_data
