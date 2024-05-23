
import os
from typing import Tuple
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from datetime import datetime

from llm_utils.database import write_to_db

from ScopingReview.upload import FastAPIUploadManager
from ScopingReview.compile import FastAPIBibtexManager
import ScopingReview_config.config as lit_config
import ScopingReview_config.app_config as lit_app_config


from app.v01.schemas import SearchRequest
import app.fastapi_config as lit_api_config

# TODO: meta data
router = APIRouter(tags=["standalone", "bibliography"])

async def get_bibtex_response(file: UploadFile) -> Response:
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["xlsx", "docx"])
        # Handles both .docx and .xlsx files
        content, file_ext = await upload_manager.upload_file(file)  
        if content is None:
            raise HTTPException(status_code=422, detail="Failed to process the file or unsupported file type")
        
        bibtex_manager = FastAPIBibtexManager(content, file_ext)
        # Creating the response
        response = bibtex_manager.convert_and_download_bibtex()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response

    
@router.post("/search/v01/standalone/bibliography/", **lit_api_config.STANDALONE_BIBLIOGRAPHY_META)
async def initial_literature_search(file: UploadFile) -> Response:
    response = await get_bibtex_response(file)
    return response