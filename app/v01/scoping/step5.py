from fastapi import APIRouter, HTTPException, BackgroundTasks
import datetime
from llm_utils.database import write_to_db
from ScopingReview.compile import FastAPIDraftReviewManager
from ScopingReview.upload import FastAPIUploadManager
import ScopingReview_config.app_config as lit_app_config
import os
import app.fastapi_config as lit_api_config
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import DraftRequest
from llm_utils import api_utils

router = APIRouter(tags=["scoping", "step5"])

def get_step5_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    docx_encoded: str) -> MSWordResponse:

    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager()
        summaries_markdown = upload_manager.read_and_validate_file(docx_encoded, ".docx")
        if summaries_markdown is None:
            raise HTTPException(status_code=422, detail="Failed to process the file or unsupported file type")

        draft_manager = FastAPIDraftReviewManager(summaries_markdown, research_question)
        docx_data = draft_manager.draft_review()
        temp_file_path = draft_manager.save_draft_review(docx_data)
        encoded_file = api_utils.file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

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
async def draft_review(
    background_tasks: BackgroundTasks,
    request: DraftRequest,
    ) -> MSWordResponse:
    """
    Processes an uploaded DOCX file containing summaries, generates a draft review based on a specified research question, 
    and returns a downloadable DOCX file with the draft review.

    This endpoint facilitates the drafting of a detailed review document by processing provided summaries
    and integrating them with a user-specified research question. It is particularly useful in research and academic 
    contexts where initial summaries need to be expanded into comprehensive draft reviews.
    """
    response = get_step5_response(
        background_tasks,
        request.research_question,
        request.docx_encoded
        )
    return response
