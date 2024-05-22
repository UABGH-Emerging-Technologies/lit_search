from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from typing import Tuple
import datetime
from llm_utils.database import write_to_db
from ScopingReview.compile import FastAPIDraftReviewManager
from ScopingReview.upload import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config

router = APIRouter(tags=["scoping", "step5"])

async def get_step5_response(background_tasks: BackgroundTasks, research_question: str, file: UploadFile) -> Tuple[str, FileResponse]:
    """
    This function uploads a file, processes it, generates a draft review, saves it as a file, and logs
    relevant information to a database.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is an instance of the
    `BackgroundTasks` class in FastAPI. It allows you to add background tasks to be run after the
    response is sent to the client. In your code snippet, you are using it to add a task to write data
    to a database after processing
      research_question (str): The `research_question` parameter is a string that represents the
    question or topic for which the draft review is being conducted. It is used as input to generate the
    draft review document.
      file (UploadFile): The `file` parameter in the `get_step5_response` function is of type
    `UploadFile`. This parameter is used to receive an uploaded file from the client. The function then
    processes this file to generate a response.
    
    Returns:
      The function `get_step5_response` returns a tuple containing the temporary file path where the
    processed file is saved and a `FileResponse` object that includes the path, filename, and media type
    of the saved file.
    """
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["docx"])
        summaries_markdown = await upload_manager.upload_file(file)
        if summaries_markdown is None:
            raise HTTPException(status_code=422, detail="Failed to process the file or unsupported file type")

        draft_manager = FastAPIDraftReviewManager(summaries_markdown, research_question)
        docx_data = draft_manager.draft_review()
        temp_file_path = draft_manager.save_draft_review(docx_data)
        response = FileResponse(
            path=temp_file_path, 
            filename=draft_manager.get_filename(),
            media_type=draft_manager.get_mime_type(),
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
            draft_manager.cost,
            "_scoping_step5_draft"
        )
    except KeyError:
        pass

    return temp_file_path, response

@router.post("/search/v01/scoping/step5/", **lit_api_config.SCOPING_STEP5_META)
async def draft_review(background_tasks: BackgroundTasks, research_question: str, file: UploadFile = File(...)) -> FileResponse:
    """
    Processes an uploaded DOCX file containing summaries, generates a draft review based on a specified research question, 
    and returns a downloadable DOCX file with the draft review.

    This endpoint facilitates the drafting of a detailed review document by processing provided summaries
    and integrating them with a user-specified research question. It is particularly useful in research and academic 
    contexts where initial summaries need to be expanded into comprehensive draft reviews.

    Args:
        research_question (str): The research question that guides the drafting process. This question forms the basis
        of the review, influencing how the summaries are integrated and presented in the final document.
        file (UploadFile): The DOCX file uploaded by the user. This file should contain the summaries
        that will be processed into a draft review. Defaults to File(...), indicating that a file must be provided.

    Returns:
        FileResponse: A response object that facilitates the direct download of the draft review document. The file is
        returned as a DOCX document, which is suitable for academic and professional review.

    Raises:
        HTTPException: If the file cannot be processed or if the file type is unsupported, a 422 error is returned with
        an explanation of the issue.
        HTTPException: If any internal server errors occur during the processing, a 500 error is returned with a message
        describing the problem.

    Usage:
        The endpoint is designed to be used as part of a research scoping or review process, where quick generation of
        draft documents from preliminary summaries is required. It accepts a file upload directly through a client
        interface, such as a web form, and outputs a formatted DOCX file that can be immediately downloaded and reviewed.
    """
    temp_file_path, response = await get_step5_response(background_tasks, research_question, file)
    background_tasks.add_task(os.unlink, temp_file_path)
    return response
