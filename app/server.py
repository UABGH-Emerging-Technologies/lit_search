import uvicorn
from fastapi import FastAPI

from app import api_config
from app.v01.standalone.summary import router as v01_standalone_summary_router
from app.v01.scoping.step1 import router as v01_scoping_step1_router

app = FastAPI(**api_config.LIT_API_META)

app.include_router(v01_standalone_summary_router)
app.include_router(v01_scoping_step1_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
