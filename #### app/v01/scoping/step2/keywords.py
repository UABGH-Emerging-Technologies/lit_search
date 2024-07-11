from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from ScopingReview.workflows import SummarizeWorkflow
from ScopingReview_config import app_config
from app.v01.scoping.schemas import KeywordsData
from app.v01.scoping.step2.schemas import KeywordsRequest
from app.fastapi_config import SCOPING_STEP2KEYWORDS_META

router = APIRouter(tags=["scoping", "step2"])

def get_step2keywords_response(background_tasks: BackgroundTasks, question: str, xlsx_encoded: str) -> KeywordsData:
    start = datetime.now()
    try:
        workflow = SummarizeWorkflow(question)
        df = workflow.read_and_validate_file(xlsx_encoded, ".xlsx")
        keywords = workflow.process()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finish = datetime.now()

    content_to_log = f'{{"question":"{question}"}}'
    workflow.log_to_database(app_config, content_to_log, start, finish, background_tasks, label="_scoping_step2")
    
    return keywords

@router.post("/search/v01/scoping/step2/keywords/", **SCOPING_STEP2KEYWORDS_META)
async def suggest_keywords(background_tasks: BackgroundTasks, request: KeywordsRequest) -> KeywordsData:
    return get_step2keywords_response(background_tasks, request.research_question, request.xlsx_encoded)
