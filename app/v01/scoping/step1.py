#####
# Step 1 is the initial search
#####

import os
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from aiweb_common.file_operations.file_handling import file_to_base64

from ScopingReview.InitialSearch.Workflow import ArticleSearch
import ScopingReview_config.app_config as app_config
import ScopingReview_config.config as config
from app.v01.schemas import SearchRequest, MSExcelResponse
import app.fastapi_config as lit_api_config
import tempfile

# TODO: metadata
router = APIRouter(tags=["scoping", "step1"])

def get_step1_response(
    background_tasks: BackgroundTasks,
    research_question: str
) -> MSExcelResponse:
    """
    This function performs an initial literature search based on a research question, saves the search
    results to an Excel file, and logs the search details to a database.
    """
    start = datetime.now()

    try:
        # Utilizing the new ArticleSearch to perform the literature search
        article_search = ArticleSearch(research_question)
        # TODO: all .process() methods should return either a df or md-as-a-string
        articles_df = article_search.process()
        if articles_df is None:
            raise HTTPException(status_code=404, detail="No articles found")
        # TODO: a special function should then convert to a tempfile
        # make this part of base manager
        articles_file = article_search.get_tempfile_excel(articles_df, research_question)
        
        encoded_file = file_to_base64(articles_file)
        background_tasks.add_task(os.unlink, articles_file)
        response = MSExcelResponse(encoded_xlsx=encoded_file)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.now()

    try:
        # Adding a background task to write search details to the database
        content_to_log = f'{{"query":"{research_question}"}}'
        article_search.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step1")
    except KeyError:
        pass

    return response

@router.post("/search/v01/scoping/step1/", **lit_api_config.SCOPING_STEP1_META)
async def perform_step1_scoping_search(
    background_tasks: BackgroundTasks,
    query: SearchRequest
    ) -> MSExcelResponse:
    """
    Conducts an initial literature search based on the provided research question, compiles the results into an Excel file, and returns the file for download. This endpoint is particularly useful for the early stages of a scoping review or literature review, providing a comprehensive collection of relevant literature.

    This method leverages advanced search algorithms to query multiple databases, ensuring a thorough exploration of available literature. The search results are then compiled into an Excel file which is made available for immediate download. Additionally, details of the search are recorded in a database for audit and research purposes.
    """
    return get_step1_response(
        background_tasks, query.research_question
    )
