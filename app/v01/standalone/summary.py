from fastapi import APIRouter, BackgroundTasks, HTTPException
import ScopingReview_config.app_config as app_config

from datetime import datetime

from ScopingReview.Standalone.Workflow import StandaloneSummary
from app.v01.schemas import SearchRequest, MSWordResponse
import app.fastapi_config as api_config

# TODO: meta data
router = APIRouter(tags=["standalone", "summary"])

def get_summary_response(
    background_tasks: BackgroundTasks,
    research_question: str
    ) -> MSWordResponse:

    start = datetime.now()
    
    try:
        # Perform initial literature search and get DataFrame
        standalone_search = StandaloneSummary(research_question)
        overview_md = standalone_search.process()

        encoded_file = standalone_search.searcher.search_manager.get_encoded_docx(overview_md, background_tasks)
        response = MSWordResponse(encoded_docx=encoded_file)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    
    try:
        # Adding a background task to write search details to the database
        content_to_log = f'{{"query":"{research_question}"}}'
        standalone_search.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_standalone")
    except KeyError:
        pass

    return response


@router.post("/search/v01/standalone/summary/", **api_config.STANDALONE_SUMMARY_META)
async def initial_literature_search(
    background_tasks: BackgroundTasks,
    query: SearchRequest
    ) -> MSWordResponse:
    """
    Performs an initial literature search based on a provided research question, summarizes the findings, and generates a downloadable DOCX file containing the summary. This method leverages automated search and summarization tools to provide a concise overview of relevant literature.

    The process includes:
    - Searching for articles related to the research question.
    - Compiling and summarizing the most relevant articles.
    - Generating a summary document in DOCX format.

    Parameters:
        query (SearchRequest): A data model that includes the research question for which the literature search and summary need to be conducted.

    Returns:
        FileResponse: A response object that includes the file data for the generated summary. The file is temporarily stored and is available for download immediately after generation. Post-download, the file is cleaned up from the server to maintain security and efficiency.
    
    Raises:
        HTTPException: Returns a 404 error if no articles are found, or a 500 error for any other processing failures during the search and summary generation process.
    """
    
    response = get_summary_response(
        background_tasks, query.research_question
    )
    return response