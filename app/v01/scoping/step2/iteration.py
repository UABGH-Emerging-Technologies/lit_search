from datetime import datetime

from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException

import app.fastapi_config as api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.step2.schemas import IterationRequest
from app.v01.scoping.step2.validators import validate_keywords_data
from ScopingReview.IterateSearch.Workflow import IterateSearch
from ScopingReview.Keywords.Manager import KeywordData
from ScopingReview_config import app_config

# TODO: metadata
router = APIRouter(tags=["scoping", "step2"])


def get_step2iteration_response(
    background_tasks: BackgroundTasks, question: str, xlsx_encoded: str, keywords: KeywordData
) -> MSExcelResponse:
    """
    This function processes an uploaded Excel file, performs a search based on a question and keywords,
    and returns the search results in an encoded Excel file while also writing relevant data to a
    database.

    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is used to handle background
    tasks in FastAPI. It allows you to perform tasks asynchronously, such as file processing or database
    operations, without blocking the main request-response cycle. In the provided function
    `get_step2iteration_response`, the `background_tasks` parameter is an instance
      question (str): The `question` parameter in the `get_step2iteration_response` function is a string
    that represents the question or query for which you want to perform a search or analysis on the data
    provided in the uploaded Excel file. It is used by the `FastAPIIterateSearchManager` to perform the
      xlsx_encoded (str): The `xlsx_encoded` parameter in the `get_step2iteration_response` function is
    a string that represents the encoded content of an Excel file. This encoded content is typically
    used for uploading and processing Excel files within the function.
      keywords (KeywordsData): The `keywords` parameter in the `get_step2iteration_response` function is
    of type `KeywordsData`. It likely contains information related to keywords used for searching or
    filtering data.

    Returns:
      The function `get_step2iteration_response` returns an instance of `MSExcelResponse`, which
    contains an encoded Excel file (`encoded_xlsx`).
    """
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        iterate_search = IterateSearch(df, question, keywords)
        articles_df, refined_query = iterate_search.process()
        encoded_file = iterate_search.search_manager.get_encoded_excel(
            articles_df, background_tasks, pubmed_query="refined_query"
        )
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()

    content_to_log = f'{{"query":"{question}", "Refined Query":"{refined_query}"}}'
    iterate_search.log_to_database(
        app_config, content_to_log, start, finish, background_tasks, label="_scoping_step2b_iterate"
    )

    return response


@router.post("/search/v01/scoping/step2/iteration/", **api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(
    background_tasks: BackgroundTasks,
    request: IterationRequest,
) -> MSExcelResponse:
    """
    This Python function updates keywords and performs a search based on the provided request data.
    """

    keywords = validate_keywords_data(
        request.primary_keywords, request.secondary_keywords, request.exclusion_keywords
    )

    response = get_step2iteration_response(
        background_tasks, request.research_question, request.xlsx_encoded, keywords
    )
    return response
