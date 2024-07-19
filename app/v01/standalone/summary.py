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
    """
    Perform a literature search based on a given research question, summarize the findings,
    and returns a downloadable DOCX response with the summary. 

    This function uses a standalone summary instance to process the research question,
    encode the summary findings as a DOCX file, and return it as a response. If any 
    processing failure occurs during this process, an HTTP error is raised.

    After the main function logic, a background task logs the research query and the 
    execution time to the database, ignoring any KeyError.

    Parameters:
    background_tasks (BackgroundTasks): FastAPI background tasks for performing operations
    after returning the response.
    research_question (str): The research question for which the literature search and 
    summary need to be conducted.

    Returns:
    MSWordResponse: A response object that includes the file data for the generated summary. 

    Raises:
    HTTPException: Returns a 500 error for any processing failures during the search and 
    summary generation process.
    """

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
    This function performs a literature search based on a given research question, summarizes the findings, and provides a downloadable DOCX summary, returning an error if no articles are found or if any issue arises during the process.
    """
    response = get_summary_response(
        background_tasks, query.research_question
    )
    return response