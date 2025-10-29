from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
import base64
import app.fastapi_config as api_config
from app.v01.schemas import MSWordResponse, SearchRequest
from ScopingReview.Standalone.Workflow import StandaloneSummary
from app.dependencies import security, get_api_key

router = APIRouter(tags=["standalone", "summary"])


def get_summary_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> MSWordResponse:
    start = datetime.now()
    try:
        standalone_search = StandaloneSummary(
            research_question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        overview_md = standalone_search.process()
        with open(overview_md, "rb") as f:
            docx_bytes = f.read()
        encoded_file = base64.b64encode(docx_bytes).decode("utf-8")
        response = MSWordResponse(encoded_docx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/search/v01/standalone/summary/", **api_config.STANDALONE_SUMMARY_META)
async def initial_literature_search(
    background_tasks: BackgroundTasks,
    query: SearchRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSWordResponse:
    """
    Performs initial literature search and generates summary.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)
    
    response = get_summary_response(
        background_tasks,
        query.research_question,
        query.openai_compatible_endpoint,
        api_key,
        query.openai_compatible_model,
    )
    return response