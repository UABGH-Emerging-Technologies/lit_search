import logging
import os
from datetime import datetime

from aiweb_common.file_operations.file_handling import file_to_base64
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials

import app.fastapi_config as api_config
from app.dependencies import get_api_key, security
from app.v01.schemas import MSWordResponse, SearchRequest
from ScopingReview.Standalone.Workflow import StandaloneSummary

router = APIRouter(tags=["standalone", "summary"])
logger = logging.getLogger("app_logger")


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
        temp_file_path = standalone_search.process()
        encoded_file = file_to_base64(temp_file_path)
        background_tasks.add_task(os.unlink, temp_file_path)
        response = MSWordResponse(encoded_docx=encoded_file)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in get_summary_response")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    return response


@router.post("/v01/standalone/summary/", **api_config.STANDALONE_SUMMARY_META)
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
