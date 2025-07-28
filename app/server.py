import logging
import uvicorn
from aiweb_common.fastapi.helper_apis import router as utils_router
from fastapi import FastAPI, Request
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

# Middleware to log requests and exceptions
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        try:
            response = await call_next(request)
            logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
            return response
        except Exception as e:
            logger.error(f"Exception during request: {request.method} {request.url} - {e}", exc_info=True)
            raise

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
