import datetime

from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials

import app.fastapi_config as api_config
from app.dependencies import get_api_key, security
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import DraftRequest
from ScopingReview.Draft.Workflow import DraftReview

router = APIRouter(tags=["scoping", "step5"])


def get_step5_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    docx_encoded: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> MSWordResponse:
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks)
        summaries_markdown = upload_manager.read_and_validate_file(docx_encoded, ".docx")
        if summaries_markdown is None:
            raise HTTPException(
                status_code=422, detail="Failed to process the file or unsupported file type"
            )

        drafting = DraftReview(
            summaries_markdown,
            research_question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        draft_md = drafting.process()
        encoded_file = drafting.drafter.get_encoded_docx(draft_md, background_tasks)
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/v01/scoping/step5/", **api_config.SCOPING_STEP5_META)
async def draft_review(
    background_tasks: BackgroundTasks,
    request: DraftRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSWordResponse:
    """
    Processes uploaded DOCX file and generates draft review.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)

    response = get_step5_response(
        background_tasks,
        request.research_question,
        request.docx_encoded,
        request.openai_compatible_endpoint,
        api_key,
        request.openai_compatible_model,
    )
    return response
