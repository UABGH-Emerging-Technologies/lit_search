from fastapi import File, UploadFile, APIRouter, HTTPException, BackgroundTasks, Depends


from datetime import datetime

from llm_utils.database import write_to_db

import ScopingReview_config.app_config as lit_app_config
from ScopingReview.search import FastAPIIterateSearchManager
from ScopingReview.upload import FastAPIUploadManager
import app.fastapi_config as lit_api_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.schemas import SearchRequest

# TODO: metadata
router = APIRouter(tags=["scoping", "step2"])


async def get_step2keywords_response(background_tasks: BackgroundTasks, question: str, file: UploadFile) -> KeywordsData:
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["xlsx"])
        df, _ = await upload_manager.upload_file(file)
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        manager = FastAPIIterateSearchManager(df, question)
        keywords, cost = manager.extract_and_return_keywords()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finish = datetime.now()
    try:
        background_tasks.add_task(
            write_to_db,
            lit_app_config,
            f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}',
            start,
            finish,
            cost,
            "_scoping_step2_keywords",
        )
    except KeyError:
        pass
    return keywords


@router.post("/search/v01/scoping/step2/keywords/", **lit_api_config.SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(background_tasks: BackgroundTasks, query: SearchRequest = Depends(), file: UploadFile = File(...)) -> KeywordsData:
    keywords = await get_step2keywords_response(background_tasks, query.research_question, file)
    return keywords