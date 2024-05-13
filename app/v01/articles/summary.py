
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


from app.v01.articles.schemas import SearchRequest, SearchType
import app.api_config as lit_api_config


router = APIRouter()

async def get_summary_response(
    background_tasks: BackgroundTasks,
    research_question: str
) -> Tuple[str, FileResponse]:
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

@router.post("/search/v01/articles/summary/")
async def initial_literature_search(background_tasks: BackgroundTasks, query: SearchRequest):
    # Instantiate the search manager with the query
    
    temp_file_path, response = await get_summary_response(
        background_tasks, query.research_question
    )
    background_tasks.add_task(os.unlink, temp_file_path)  # Schedule cleanup of the temp file
    return response