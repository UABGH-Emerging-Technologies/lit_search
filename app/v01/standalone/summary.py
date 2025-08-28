from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
import base64

import app.fastapi_config as api_config
import ScopingReview_config.app_config as app_config
from app.v01.schemas import MSWordResponse, SearchRequest
from ScopingReview.Standalone.Workflow import StandaloneSummary

# TODO: meta data
router = APIRouter(tags=["standalone", "summary"])


def get_summary_response(
    background_tasks: BackgroundTasks, research_question: str
) -> MSWordResponse:

    start = datetime.now()

    try:
        # Perform initial literature search and get DataFrame
        standalone_search = StandaloneSummary(research_question)
        overview_md = standalone_search.process()

        # Read the generated DOCX file bytes and encode to base64
        with open(overview_md, "rb") as f:
            docx_bytes = f.read()

        encoded_file = base64.b64encode(docx_bytes).decode("utf-8")

        response = MSWordResponse(encoded_docx=encoded_file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/search/v01/standalone/summary/", **api_config.STANDALONE_SUMMARY_META)
async def initial_literature_search(
    background_tasks: BackgroundTasks, query: SearchRequest
) -> MSWordResponse:
    """
    Performs an initial literature search based on a provided research question, summarizes the findings, and generates a downloadable DOCX file containing the summary. This method leverages automated search and summarization tools to provide a concise overview of relevant literature.
    """

    response = get_summary_response(background_tasks, query.research_question)
    return response
