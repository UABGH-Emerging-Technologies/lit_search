import datetime

from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Response,
    Security,
)
from fastapi.security import HTTPAuthorizationCredentials

import app.fastapi_config as api_config
from app.dependencies import get_api_key, security
from app.v01.schemas import MSWordResponse
from app.v01.scoping.schemas import SummariesRequest
from ScopingReview.Summarize.Workflow import SummarizeArticles

router = APIRouter(tags=["scoping", "step4"])


def get_step4_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    xlsx_encoded: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
):
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        summarization = SummarizeArticles(
            df,
            research_question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        summaries_md, warning_msg = summarization.process()
        encoded_file = summarization.summarizer.get_encoded_docx(summaries_md, background_tasks)
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response, warning_msg


@router.post("/v01/scoping/step4/", **api_config.SCOPING_STEP4_META)
async def summarize_articles(
    background_tasks: BackgroundTasks,
    request: SummariesRequest,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSWordResponse:
    """
    Receives uploaded Excel file and generates summaries.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)

    response_data, warning_message = get_step4_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded,
        request.openai_compatible_endpoint,
        api_key,
        request.openai_compatible_model,
    )
    if warning_message:
        response.headers["Warning"] = warning_message
    return response_data
