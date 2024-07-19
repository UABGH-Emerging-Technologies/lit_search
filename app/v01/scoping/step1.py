from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException

from ScopingReview.InitialSearch.Workflow import ArticleSearch
import ScopingReview_config.app_config as app_config
from app.v01.schemas import SearchRequest, MSExcelResponse
import app.fastapi_config as api_config

# TODO: metadata
router = APIRouter(tags=["scoping", "step1"])

def get_step1_response(
    background_tasks: BackgroundTasks,
    research_question: str
) -> MSExcelResponse:
    """
    The function `get_step1_response` performs a literature search based on a research question,
    generates an Excel file with search results, and logs search details to a database as a background
    task.
    
    Args:
      background_tasks (BackgroundTasks): `BackgroundTasks` is a class provided by FastAPI for handling
    background tasks. It allows you to run tasks asynchronously in the background. In this function,
    `background_tasks` is used to handle tasks such as writing search details to the database without
    blocking the main request-response cycle.
      research_question (str): The `get_step1_response` function takes in two parameters:
    
    Returns:
      The function `get_step1_response` returns an instance of `MSExcelResponse` containing an encoded
    Excel file.
    """
    start = datetime.now()

    try:
        # Utilizing the new ArticleSearch to perform the literature search
        article_search = ArticleSearch(research_question)
        articles_df = article_search.process()
        if articles_df is None:
            raise HTTPException(status_code=404, detail="No articles found")
        encoded_file = article_search.search_manager.get_encoded_excel(articles_df, background_tasks, research_question)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()


    # Adding a background task to write search details to the database
    content_to_log = f'{{"query":"{research_question}"}}'
    article_search.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step1")

    return response

@router.post("/search/v01/scoping/step1/", **api_config.SCOPING_STEP1_META)
async def perform_step1_scoping_search(
    background_tasks: BackgroundTasks,
    query: SearchRequest
    ) -> MSExcelResponse:
    """
    This function conducts an initial literature search based on a research question, compiles the
    results into an Excel file, and returns it for download.
    
    Args:
      background_tasks (BackgroundTasks): BackgroundTasks - A class that allows you to add background
    tasks to be run after returning a response in FastAPI. These tasks are run asynchronously after the
    response has been sent to the client, making them useful for operations that should not delay the
    response to the client.
      query (SearchRequest): The `query` parameter in the `perform_step1_scoping_search` function
    represents a `SearchRequest` object, which likely contains information related to the research
    question for which the literature search is being conducted. This object may include details such as
    keywords, filters, search criteria, and any other relevant
    
    Returns:
      MSExcelResponse
    """
    return get_step1_response(
        background_tasks, query.research_question
    )
