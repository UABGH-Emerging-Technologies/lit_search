import uvicorn
from fastapi import FastAPI

from app import api_config
from app.v01.articles.summary import router as v01_articles_summary_router

app = FastAPI(**api_config.LIT_API_META)
app.include_router(v01_articles_summary_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
