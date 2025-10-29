import logging
import uvicorn
from aiweb_common.fastapi.helper_apis import router as utils_router
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app import fastapi_config
from app.v01.scoping.step1 import router as v01_scoping_step1_router
from app.v01.scoping.step2.iteration import (
    router as v01_scoping_step2iteration_router,
)
from app.v01.scoping.step2.keywords import (
    router as v01_scoping_step2keywords_router,
)
from app.v01.scoping.step3 import router as v01_scoping_step3_router
from app.v01.scoping.step4 import router as v01_scoping_step4_router
from app.v01.scoping.step5 import router as v01_scoping_step5_router
from app.v01.standalone.bibliography import (
    router as v01_standalone_bibliography_router,
)
from app.v01.standalone.summary import router as v01_standalone_summary_router

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app_logger")

app = FastAPI(**fastapi_config.LIT_API_META)

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import status
from fastapi.encoders import jsonable_encoder

def sanitize_bytes_in_obj(obj):
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, dict):
        return {k: sanitize_bytes_in_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_bytes_in_obj(i) for i in obj]
    else:
        return obj

@app.exception_handler(RequestValidationError)
async def custom_request_validation_exception_handler(request, exc):
    """Handle validation errors (422)"""
    sanitized_errors = sanitize_bytes_in_obj(exc.errors())
    content = {"detail": sanitized_errors}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(content),
    )

@app.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    """Handle all exceptions, including non-HTTP exceptions"""
    from fastapi import HTTPException
    
    # If it's an HTTPException, handle it properly
    if isinstance(exc, HTTPException):
        detail = exc.detail
        sanitized_detail = sanitize_bytes_in_obj(detail)
        content = {"detail": sanitized_detail}
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(content),
            headers=getattr(exc, "headers", None),
        )
    
    # For regular exceptions (not HTTPException), return 500
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# Middleware to log requests - FIXED: removed exception handling to let exception handler work
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
        return response

app.add_middleware(LoggingMiddleware)

app.include_router(v01_standalone_summary_router)
app.include_router(v01_standalone_bibliography_router)
app.include_router(v01_scoping_step1_router)
app.include_router(v01_scoping_step2keywords_router)
app.include_router(v01_scoping_step2iteration_router)
app.include_router(v01_scoping_step3_router)
app.include_router(v01_scoping_step4_router)
app.include_router(v01_scoping_step5_router)
app.include_router(utils_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/process")
async def process_request(
    request: Request,
    authorization: str = Header(..., description="Bearer token for authentication"),
):
    if authorization is None:
        raise HTTPException(status_code=400, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid authorization header format")
    
    api_key = authorization.split(" ")[1]
    body = await request.json()
    openai_compatible_endpoint = body.get("openai_compatible_endpoint")
    openai_compatible_model = body.get("openai_compatible_model")
    
    # Validate required fields
    if not openai_compatible_endpoint or not openai_compatible_model:
        raise HTTPException(status_code=422, detail="Missing required fields")
    
    # Simulate invalid API key handling
    if api_key == "invalid_key":
        raise HTTPException(status_code=500, detail="Invalid API Key")

    return {"message": "Request processed successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")