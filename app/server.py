import uvicorn
from aiweb_common.fastapi.helper_apis import router as utils_router
from fastapi import FastAPI

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

app = FastAPI(**fastapi_config.LIT_API_META)

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
