
import os
from typing import Tuple
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from datetime import datetime

from llm_utils import api_utils
from llm_utils.database import write_to_db

from ScopingReview.search import APISearchManager
import ScopingReview.generate as lit_generate
import ScopingReview_config.config as lit_config
import ScopingReview_config.app_config as lit_app_config


from app.v01.schemas import SearchRequest
import app.fastapi_config as lit_api_config

# TODO: meta data
router = APIRouter(**lit_api_config.STANDALONE_SUMMARY_META)

async def get_summary_response(
    background_tasks: BackgroundTasks,
    research_question: str
) -> Tuple[str, FileResponse]:
    """
    This async function takes a research question, performs an initial literature search using an API,
    summarizes the search results, generates a DOCX file with the summary, and writes relevant
    information to a database as a background task.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter in the `get_summary_response`
    function is used to schedule background tasks to be run after the main response has been returned to
    the client. These tasks are typically non-blocking and can be used for operations like writing to a
    database, sending emails, or other asynchronous operations that
      research_question (str): The `research_question` parameter in the `get_summary_response` function
    is a string that represents the question or topic for which the summary response is being generated.
    This question is used in the function to perform an initial literature search and compile articles
    related to the research question.
    
    Returns:
      The function `get_summary_response` returns a tuple containing the temporary file path and a
    `FileResponse` object.
    """
    start = datetime.now()

    try:
        # TODO: should we/ what's the best way to collapse this? A new class in the main package?
        # Can't have any streamlit things. They don't place nice with fastapi
        article_search_manager = APISearchManager(
           scoping_step="initial literature search",
           research_q = research_question
        )
        articles_df, cost = article_search_manager.search_and_compile_articles()
        if not articles_df.empty:
            # subclass of compile manager? Summarize manager?
            articles_df = articles_df.head(lit_config.SUBCLASS_THRESHOLD)
            articles_df["Author 1: Relevant Article? (Yes/No)"] = "Yes"
            articles_df["category"] = "Initial Search"
            articles_df["Text"] = "Text not available"
            # Unclear if it's worth making a compile class just for this next line....
            markdown_to_convert, response_meta = lit_generate.summarize_all_categories(
                    articles_df, articles_df
                )
            temp_file_path = api_utils.prepare_docx_response(markdown_to_convert)
            total_cost = cost + response_meta.total_cost
        else:
            raise HTTPException(status_code=404, detail="No articles found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    response= FileResponse(path=temp_file_path,
                    filename=lit_config.SR_STEP4_DOCX_FILENAME,
                    media_type=lit_api_config.DOCX_EXPECTED_TYPE
                    )
    try:
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"query":"{str(research_question)}"}}',
            start,
            finish,
            total_cost,
            "_standalone",
        )
    except KeyError:
        pass

    return temp_file_path, response

@router.post("/search/v01/standalone/summary/")
async def initial_literature_search(background_tasks: BackgroundTasks, query: SearchRequest):
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
    
    temp_file_path, response = await get_summary_response(
        background_tasks, query.research_question
    )
    background_tasks.add_task(os.unlink, temp_file_path)  # Schedule cleanup of the temp file
    return response