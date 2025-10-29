from datetime import datetime
from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
import app.fastapi_config as api_config
from app.v01.scoping.step2.schemas import KeywordsRequest
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from ScopingReview_config import app_config
from app.dependencies import security, get_api_key

router = APIRouter(tags=["scoping", "step2"])


def get_step2keywords_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> KeywordData:
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        
        keyword_workflow = KeywordWorkflow(
            df,
            question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        keywords = keyword_workflow.process()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return keywords


@router.post("/search/v01/scoping/step2/keywords/", **api_config.SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(
    background_tasks: BackgroundTasks,
    request: KeywordsRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> KeywordData:
    """
    Extracts keywords from research question and Excel file.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)
    
    keywords = get_step2keywords_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded,
        request.openai_compatible_endpoint,
        api_key,
        request.openai_compatible_model,
    )
    return keywords