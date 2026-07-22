from datetime import datetime
from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import app.fastapi_config as api_config
from app.v01.schemas import MSExcelResponse
from app.v01.scoping.step2.validators import validate_keywords_data
from ScopingReview.IterateSearch.Workflow import IterateSearch
from ScopingReview.Keywords.Manager import KeywordData
from app.dependencies import security, get_api_key
import logging

router = APIRouter(tags=["scoping", "step2"])
logger = logging.getLogger("app_logger")


# Pydantic model for the request
class IterationRequest(BaseModel):
    research_question: str
    primary_keywords: list[str] = Field(default_factory=list)
    secondary_keywords: list[str] = Field(default_factory=list)
    exclusion_keywords: list[str] = Field(default_factory=list)
    xlsx_encoded: str
    openai_compatible_endpoint: str
    openai_compatible_model: str


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
    
    logger.info("=" * 60)
    logger.info("STEP 2 ITERATION - Starting processing")
    logger.info(f"Research question: {question[:100]}...")  # First 100 chars
    logger.info(f"Endpoint: {openai_compatible_endpoint}")
    logger.info(f"Model: {openai_compatible_model}")
    logger.info(f"API Key present: {bool(openai_compatible_key)}")
    logger.info(f"API Key length: {len(openai_compatible_key) if openai_compatible_key else 0}")
    logger.info(f"Keywords: {keywords}")
    logger.info("=" * 60)

    try:
        logger.info("Creating upload manager...")
        upload_manager = FastAPIUploadManager(background_tasks=background_tasks)
        
        logger.info("Attempting to decode and validate Excel file...")
        try:
            df = upload_manager.read_and_validate_file(xlsx_encoded, extension=".xlsx")
            logger.info(f"Successfully decoded Excel file. Shape: {df.shape if df is not None else 'None'}")
        except (UnicodeDecodeError, binascii.Error) as decode_err:
            logger.error(f"Failed to decode Excel file: {decode_err}")
            raise HTTPException(
                status_code=422,
                detail="Failed to decode the uploaded Excel file. Please ensure it is a valid base64-encoded XLSX file."
            ) from decode_err
            
        if df is None:
            logger.error("DataFrame is None after validation")
            raise HTTPException(status_code=422, detail="Failed to process the file")

        logger.info("Creating IterateSearch workflow instance...")
        iterate_search = IterateSearch(
            df,
            question,
            keywords,
            openai_compatible_endpoint,
            openai_compatible_key,
            openai_compatible_model,
        )
        
        logger.info("Calling iterate_search.process()...")
        articles_df, refined_query = iterate_search.process()
        
        logger.info(f"Process completed. Articles DF is None: {articles_df is None}")
        if articles_df is not None:
            logger.info(f"Articles DataFrame shape: {articles_df.shape}")
            logger.info(f"Refined query: {refined_query}")
        
        # Defensive check: if the upstream search returned None (no articles found / failure),
        # raise a clear 422 to surface a validation-like error to clients/tests instead of
        # letting subsequent attribute access trigger a 500.
        if articles_df is None:
            logger.warning("Upstream search workflow returned None")
            raise HTTPException(
                status_code=422,
                detail="Upstream search workflow returned no articles (articles_df is None)."
            )
        
        logger.info("Encoding Excel file for response...")
        encoded_file = iterate_search.search_manager.get_encoded_excel(
            articles_df, background_tasks, pubmed_query=refined_query
        )
        
        logger.info(f"Successfully encoded file. Length: {len(encoded_file)}")
        response = MSExcelResponse(encoded_xlsx=encoded_file)
        
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"Step 2 iteration completed successfully in {elapsed:.2f}s")
        
        return response
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error("=" * 60)
        logger.error("UNHANDLED EXCEPTION in get_step2iteration_response")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.exception("Full traceback:")
        logger.error("=" * 60)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/v01/scoping/step2/iteration/", **api_config.SCOPING_STEP2EXCEL_META)
async def update_keywords_and_search(
    background_tasks: BackgroundTasks,
    request: IterationRequest,  # Changed from Form parameters to Pydantic model
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> MSExcelResponse:
    """
    Performs iteration search with keywords.
    Accepts JSON request body with research question, keywords, and base64-encoded Excel file.
    Requires API key in Authorization header (Bearer scheme).
    """
    logger.info("=" * 60)
    logger.info("ENDPOINT HIT: /v01/scoping/step2/iteration/")
    logger.info(f"Research question: {request.research_question}")
    logger.info(f"Primary keywords: {request.primary_keywords}")
    logger.info(f"Secondary keywords: {request.secondary_keywords}")
    logger.info(f"Exclusion keywords: {request.exclusion_keywords}")
    logger.info(f"Endpoint: {request.openai_compatible_endpoint}")
    logger.info(f"Model: {request.openai_compatible_model}")
    logger.info(f"Excel file length: {len(request.xlsx_encoded)}")
    logger.info("=" * 60)
    
    api_key = await get_api_key(credentials)
    logger.info(f"API key retrieved. Present: {bool(api_key)}, Length: {len(api_key) if api_key else 0}")
    
    logger.info("Validating keywords...")
    keywords = validate_keywords_data(
        request.primary_keywords,
        request.secondary_keywords,
        request.exclusion_keywords,
    )
    logger.info(f"Keywords validated: {keywords}")
    
    response = get_step2iteration_response(
        background_tasks,
        request.research_question,
        request.xlsx_encoded,
        keywords,
        request.openai_compatible_endpoint,
        api_key,
        request.openai_compatible_model,
    )
    
    return response