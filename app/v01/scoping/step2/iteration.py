from datetime import datetime
from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Form, Security
from fastapi.security import HTTPAuthorizationCredentials
import app.fastapi_config as api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.step2.validators import validate_keywords_data
from ScopingReview.IterateSearch.Workflow import IterateSearch
from ScopingReview.Keywords.Manager import KeywordData
from app.dependencies import security, get_api_key

router = APIRouter(tags=["scoping", "step2"])


def get_step2iteration_response(
    background_tasks: BackgroundTasks,
    question: str,
    xlsx_encoded: str,
    keywords: KeywordData,
    openai_compatible_endpoint: str,
    openai_compatible_key: str,
    openai_compatible_model: str,
) -> MSExcelResponse:
    start = datetime.now()
    import binascii

    try:
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        try:
            df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
        except (UnicodeDecodeError, binascii.Error) as decode_err:
            raise HTTPException(
                status_code=422,
                detail="Failed to decode the uploaded Excel file. Please ensure it is a valid base64-encoded XLSX file."
            ) from decode_err
        if df is None:
            raise HTTPException(status_code=422, detail="Failed to process the file")

        iterate_search = IterateSearch(
            df,
            question,
            keywords,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        articles_df, refined_query = iterate_search.process()
        # Defensive check: if the upstream search returned None (no articles found / failure),
        # raise a clear 422 to surface a validation-like error to clients/tests instead of
        # letting subsequent attribute access trigger a 500.
        if articles_df is None:
            raise HTTPException(
                status_code=422,
                detail="Upstream search workflow returned no articles (articles_df is None)."
            )
        encoded_file = iterate_search.search_manager.get_encoded_excel(
            articles_df, background_tasks, pubmed_query="refined_query"
        )
        response = MSExcelResponse(encoded_xlsx=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/search/v01/scoping/step2/iteration/", **api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(
    background_tasks: BackgroundTasks,
    research_question: str = Form(""),
    primary_keywords: str = Form(""),
    secondary_keywords: str = Form(""),
    exclusion_keywords: str = Form(""),
    openai_compatible_endpoint: str = Form(None),  # ← Optional, will use env var if not provided
    openai_compatible_model: str = Form(None),      # ← Optional, will use env var if not provided
    xlsx_encoded: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSExcelResponse:
    """
    This endpoint accepts multipart/form-data where the Excel file is provided
    as a base64-encoded string along with other form fields.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)
    
    import logging
    import os
    logger = logging.getLogger("app_logger")
    logger.debug(f"Received form fields: research_question={research_question}")
    
    def split_keywords(s: str) -> list[str]:
        return [kw.strip() for kw in s.split(",") if kw.strip()]
    
    keywords = validate_keywords_data(
        split_keywords(primary_keywords),
        split_keywords(secondary_keywords),
        split_keywords(exclusion_keywords),
    )
    
    # Use form values if provided, otherwise fall back to environment variables
    endpoint = openai_compatible_endpoint or os.getenv("OPENAI_COMPATIBLE_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    model = openai_compatible_model or os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4")
    
    response = get_step2iteration_response(
        background_tasks,
        research_question,
        xlsx_encoded,
        keywords,
        endpoint,
        api_key,
        model,
    )
    
    return response
