
import os
from typing import Tuple
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse

from datetime import datetime

from llm_utils.database import write_to_db

from ScopingReview.search import FastAPISearchManager
import ScopingReview_config.config as lit_config
import ScopingReview_config.app_config as lit_app_config


from app.v01.schemas import SearchRequest
import app.fastapi_config as lit_api_config

# TODO: metadata
router = APIRouter(tags=["scoping", "step1"])

async def get_step1_response(
    background_tasks: BackgroundTasks,
    research_question: str
) -> Tuple[str, FileResponse]:
    """
    This function performs an initial literature search based on a research question, saves the search
    results to an Excel file, and logs the search details to a database.
    """
    start = datetime.now()

    try:
        # Utilizing the new FastAPISearchManager to perform the literature search
        article_search_manager = FastAPISearchManager(
           scoping_step="initial literature search",
           research_q=research_question
        )
        temp_file_path, cost = article_search_manager.search_and_compile_articles(write_excel=True)
        if temp_file_path is None:
            raise HTTPException(status_code=404, detail="No articles found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    finish = datetime.now()
    response = FileResponse(
        path=temp_file_path,
        filename=article_search_manager.get_filename(),
        media_type=article_search_manager.get_mime_type()
    )

    try:
        # Adding a background task to write search details to the database
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"query":"{str(research_question)}"}}',
            start,
            finish,
            cost,
            "_scoping_step1",
        )
    except KeyError:
        pass

    return temp_file_path, response

@router.post("/search/v01/scoping/step1/", **lit_api_config.SCOPING_STEP1_META)
async def perform_step1_scoping_search(background_tasks: BackgroundTasks, query: SearchRequest = Depends()) -> FileResponse:
    """
    Conducts an initial literature search based on the provided research question, compiles the results into an Excel file, and returns the file for download. This endpoint is particularly useful for the early stages of a scoping review or literature review, providing a comprehensive collection of relevant literature.

    This method leverages advanced search algorithms to query multiple databases, ensuring a thorough exploration of available literature. The search results are then compiled into an Excel file which is made available for immediate download. Additionally, details of the search are recorded in a database for audit and research purposes.

    Parameters:
        query (SearchRequest): Contains the research question that drives the literature search. The question should be clearly formulated to enable precise and relevant search results.

    Returns:
        FileResponse: A file response containing the compiled search results in Excel format. The file is named according to predefined standards and contains comprehensive details of the articles found during the search.

    Raises:
        HTTPException: Returns a 404 error if no relevant articles are found, or a 500 error if there are any issues during the processing of the search or file compilation.
    """
    # Instantiate the search manager with the query
    
    temp_file_path, response = await get_step1_response(
        background_tasks, query.research_question
    )
    background_tasks.add_task(os.unlink, temp_file_path)  # Schedule cleanup of the temp file
    return response