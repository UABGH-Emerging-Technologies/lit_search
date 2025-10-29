import datetime
from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
import app.fastapi_config as api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.schemas import CategoriesRequest
from ScopingReview.Categorize.Workflow import CategorizeWorkflow
from ScopingReview_config import app_config
from app.dependencies import security, get_api_key

router = APIRouter(tags=["scoping", "step3"])


def get_step3_response(
    background_tasks: BackgroundTasks,
    user_defined_categories: str,
    xlsx_encoded: str,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> MSExcelResponse:
    start = datetime.datetime.now()
    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")
        
        categorize_workflow = CategorizeWorkflow(
            df,
            user_defined_categories,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        category_df = categorize_workflow.process()
        encoded_file = categorize_workflow.manager.get_encoded_excel(
            category_df,
            background_tasks=background_tasks,
            research_question=user_defined_categories,
        )
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/search/v01/scoping/step3/", **api_config.SCOPING_STEP3_META)
async def categorize_articles(
    background_tasks: BackgroundTasks,
    request: CategoriesRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSExcelResponse:
    """
    Processes uploaded Excel file to categorize articles.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)
    
    response = get_step3_response(
        background_tasks,
        request.user_defined_categories,
        request.xlsx_encoded,
        request.openai_compatible_endpoint,
        api_key,
        request.openai_compatible_model,
    )
    return response