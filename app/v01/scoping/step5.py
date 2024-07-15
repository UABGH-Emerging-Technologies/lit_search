from fastapi import APIRouter, HTTPException, BackgroundTasks
import datetime
from ScopingReview.Draft.Manager import FastAPIDraftReviewManager
from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
import ScopingReview_config.app_config as app_config
import os
import app.fastapi_config as lit_api_config
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import DraftRequest
from aiweb_common.file_operations.file_handling import file_to_base64

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
        encoded_file = file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.datetime.now()
    try:
      pass
        # TODO - make sure this is adapted to workflows
        # background_tasks.add_task(
        #     write_to_db,
        #     lit_app_config,
        #     f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}',
        #     start,
        #     finish,
        #     manager.total_cost,  # ensure total_cost is handled after the search
        #     "_scoping_step2_excel",
        # )
    except KeyError:
        pass

    return response

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
