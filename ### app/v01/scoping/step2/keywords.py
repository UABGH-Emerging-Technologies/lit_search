from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from ScopingReview_config import app_config
from ScopingReview.Keywords.Workflow import KeywordWorkflow
from aiweb_common.file_operations.UploadManager import FastAPIUploadManager
import app.fastapi_config as lit_api_config
from ScopingReview.Keywords.Manager import KeywordData
from app.v01.scoping.step2.schemas import KeywordsRequest

router = APIRouter(tags=["scoping", "step2"])

def get_step2keywords_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str
    ) -> KeywordData:
    start = datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df =  upload_manager.read_and_validate_file(xlsx_encoded, ".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        keyword_workflow = KeywordWorkflow(df, question)
        keywords = keyword_workflow.process()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()
    try:
        content_to_log = f'{{"primary":"{",".join(keywords.primary_keywords)}", "secondary":"{",".join(keywords.secondary_keywords)}", "exclusion":"{",".join(keywords.exclusion_keywords)}"}}'
        keyword_workflow.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step1")
    except KeyError:
        pass
    return keywords

@router.post("/search/v01/scoping/step2/keywords/", **lit_api_config.SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(
    background_tasks: BackgroundTasks,
    request: KeywordsRequest
    ) -> KeywordData:
    keywords = get_step2keywords_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded
        )
    return keywords
