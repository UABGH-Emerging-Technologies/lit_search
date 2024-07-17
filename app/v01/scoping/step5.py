from fastapi import APIRouter, HTTPException, BackgroundTasks
import datetime

from aiweb_common.file_operations.UploadManager import FastAPIUploadManager

import ScopingReview_config.app_config as lit_app_config
import app.fastapi_config as api_config
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import DraftRequest
from aiweb_common.file_operations.file_handling import file_to_base64
from ScopingReview.Draft.Workflow import DraftReview

router = APIRouter(tags=["scoping", "step5"])

def get_step5_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    docx_encoded: str) -> MSWordResponse:

    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks)
        summaries_markdown = upload_manager.read_and_validate_file(docx_encoded, ".docx")
        if summaries_markdown is None:
            raise HTTPException(status_code=422, detail="Failed to process the file or unsupported file type")

        drafting = DraftReview(summaries_markdown, research_question)
        draft_md = drafting.process()
        encoded_file = drafting.drafter.get_encoded_docx(draft_md, background_tasks)  # Convert the file to a base64 string
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.datetime.now()
    try:
        # Adding a background task to write search details to the database
        content_to_log = f'{{"query":"{research_question}"}}'
        drafting.log_to_database(
            lit_app_config,
            content_to_log,
            start,
            finish,
            background_tasks,
            label="_scoping_step5"
            )
    except KeyError:
        pass

    return response

@router.post("/search/v01/scoping/step5/", **api_config.SCOPING_STEP5_META)
async def draft_review(
    background_tasks: BackgroundTasks,
    request: DraftRequest,
    ) -> MSWordResponse:
    """
    This endpoint generates a draft review from an uploaded DOCX file of summaries based on a specified research question, and returns a downloadable DOCX file with the draft review.ts where initial summaries need to be expanded into comprehensive draft reviews.
    """
    response = get_step5_response(
        background_tasks,
        request.research_question,
        request.docx_encoded
        )
    return response
