from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials

import app.fastapi_config as api_config
from app.dependencies import get_api_key, security
from app.v01.schemas import MSExcelResponse, SearchRequest
from ScopingReview.InitialSearch.Workflow import ArticleSearch

router = APIRouter(tags=["scoping", "step1"])


def get_step1_response(
    background_tasks: BackgroundTasks,
    research_question: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> MSExcelResponse:
    """
    Performs literature search based on research question.

    Args:
        background_tasks: FastAPI background tasks
        research_question: The research question to search for
        openai_compatible_endpoint: OpenAI-compatible API endpoint URL
        openai_compatible_key: API key for authentication
        openai_compatible_model: Model name to use

    Returns:
        MSExcelResponse containing encoded Excel file
    """
    start = datetime.now()
    try:
        # Pass all required parameters to the workflow (like IRB Assistant)
        article_search = ArticleSearch(
            research_question,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        articles_df = article_search.process()
        if articles_df is None:
            raise HTTPException(status_code=404, detail="No articles found")
        encoded_file = article_search.search_manager.get_encoded_excel(
            articles_df, background_tasks, research_question
        )
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/v01/scoping/step1/", **api_config.SCOPING_STEP1_META)
async def perform_step1_scoping_search(
    background_tasks: BackgroundTasks,
    query: SearchRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSExcelResponse:
    """
    Conducts an initial literature search based on a research question, compiles the
    results into an Excel file, and returns it for download.

    Requires API key in Authorization header (Bearer scheme).
    """
    # Extract API key from Authorization header (like IRB Assistant)
    api_key = await get_api_key(credentials)

    return get_step1_response(
        background_tasks,
        query.research_question,
        query.openai_compatible_endpoint,
        api_key,  # ← API key from Authorization header
        query.openai_compatible_model,
    )
