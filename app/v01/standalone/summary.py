
import os
from typing import Tuple
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse

from datetime import datetime

from aiweb_common.file_operations.file_handling import file_to_base64

from ScopingReview.Summarize.Workflow import SummarizeArticles
from app.v01.schemas import SearchRequest, MSWordResponse
import app.fastapi_config as lit_api_config

# TODO: meta data
router = APIRouter(tags=["standalone", "summary"])

def get_summary_response(
    background_tasks: BackgroundTasks,
    research_question: str
    ) -> MSWordResponse:

    try:
        # Perform initial literature search and get DataFrame
        article_search_manager = ArticleSearchWorkflow(scoping_step="initial literature search", research_q=research_question)
        articles_df, seach_cost = article_search_manager.process()

        # Use FastAPISummarizeManager to summarize and save the result
        summarize_manager = FastAPISummarizeManager(articles_df, research_question)
        temp_file_path, compile_cost = summarize_manager.standalone_summarize_and_save()
        encoded_file = file_to_base64(temp_file_path)  # Convert the file to a base64 string

        background_tasks.add_task(os.unlink, temp_file_path)  # Cleanup temporary file
        response = MSWordResponse(encoded_docx=encoded_file)
        
        # Schedule background tasks
        total_cost = seach_cost + compile_cost
        try: 
            pass
            # TODO Replace with corresponding workflow database stuff
            # background_tasks.add_task(write_to_db,
            #                         lit_app_config,
            #                         f'{{"query":"{str(research_question)}"}}',
            #                         datetime.now(), datetime.now(),
            #                         total_cost, "_standalone")
        except KeyError:
            pass
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/search/v01/standalone/summary/", **lit_api_config.STANDALONE_SUMMARY_META)
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