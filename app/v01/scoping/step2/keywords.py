from fastapi import APIRouter, HTTPException, BackgroundTasks
import base64

from datetime import datetime

import ScopingReview_config.app_config as lit_app_config
from ScopingReview.SearchManager import FastAPIIterateSearchManager
from ScopingReview.UploadManager import FastAPIUploadManager
import app.fastapi_config as lit_api_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.scoping.step2.schemas import KeywordsRequest


router = APIRouter(tags=["scoping", "step2"])

def get_step2keywords_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str
    ) -> KeywordsData:
    """
    This function takes in a question and an Excel file, extracts keywords from the file based on the
    question, and writes the extracted keywords to a database.
    
    Args:
      background_tasks (BackgroundTasks): The `background_tasks` parameter is used to add background
    tasks to be run after the main response has been returned. In this code snippet, it is being used to
    write the extracted keywords data to a database as a background task.
      question (str): The `question` parameter in the `get_step2keywords_response` function is a string
    that represents the question for which you want to extract keywords from the provided Excel file.
    This question will be used by the function to search for relevant keywords within the Excel data.
      xlsx_encoded (bytes as str): The `xlsx_bytes` parameter in the `get_step2keywords_response` function is
    expected to be a bytes object containing the content of an Excel file (.xlsx). This parameter is
    used to read the Excel file and extract keywords based on the provided question.
    
    Returns:
      The function `get_step2keywords_response` takes in background tasks, a question, and xlsx file
    bytes as input parameters. It processes the xlsx file, extracts keywords related to the question,
    and then writes the extracted keywords to a database. Finally, it returns the extracted keywords.
    """
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager()
        df =  upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        manager = FastAPIIterateSearchManager(df, question)
        keywords, cost = manager.extract_and_return_keywords()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    try:
      pass
        # TODO - make sure this is adapted to workflows
        # background_tasks.add_task(
        #     write_to_db,
        #     lit_app_config,
        #     f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}',
        #     start,
        #     finish,
        #     manager.total_cost,  # ensure total_cost is handled after the search
        #     "_scoping_step2_excel",
        # )
    except KeyError:
        pass
    return keywords


@router.post("/search/v01/scoping/step2/keywords/", **lit_api_config.SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(
    background_tasks: BackgroundTasks,
    request: KeywordsRequest
    ) -> KeywordsData:
    """
    Get AI-suggested search keywords based on end-user labeling of relevant articles.
    """
    keywords = get_step2keywords_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded
        )
    return keywords