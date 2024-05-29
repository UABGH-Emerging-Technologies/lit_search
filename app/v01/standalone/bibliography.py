
import os
import base64

from typing import Tuple
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from datetime import datetime

from llm_utils.database import write_to_db
from llm_utils import api_utils

from ScopingReview.upload import FastAPIUploadManager
from ScopingReview.compile import FastAPIBibtexManager
import ScopingReview_config.config as lit_config
import ScopingReview_config.app_config as lit_app_config


from app.v01.schemas import UploadableFiles
from app.v01.standalone.schemas import BibliographyResponse, BibliographyRequest
import app.fastapi_config as lit_api_config

# TODO: meta data
router = APIRouter(tags=["standalone", "bibliography"])

def get_bibtex_response(
    encoded_file: bytes,
    file_extension: UploadableFiles,
    background_tasks: BackgroundTasks
    ) -> BibliographyResponse:
    """
    The function `get_bibtex_response` processes uploaded .docx and .xlsx files to generate a BibTeX
    file and returns it as a base64 encoded string in a `BibliographyResponse`.
    
    Args:
      encoded_file (str): The `encoded_file` parameter in the `get_bibtex_response` function is a string
    that represents the file content encoded in a specific format, such as base64. This encoded file
    will be used as input for processing and generating a BibliographyResponse.
      file_extension (UploadableFiles): The `file_extension` parameter in the `get_bibtex_response`
    function is of type `UploadableFiles`. It is used to specify the type of file being uploaded, which
    can be either "xlsx" for Excel files or "docx" for Word files. This parameter helps in determining
      background_tasks (BackgroundTasks): The `background_tasks` parameter in the `get_bibtex_response`
    function is used to run background tasks asynchronously. In this case, it is being used to delete a
    temporary file (`temp_file_path`) after it has been processed and the response has been generated.
    This helps in offloading tasks
    
    Returns:
      The function `get_bibtex_response` returns a `BibliographyResponse` object, which contains the
    encoded BibTeX file as a base64 string.
    """
    try:
        upload_manager = FastAPIUploadManager("Please upload your file", ["xlsx", "docx"])
        # Handles both .docx and .xlsx files
        content = upload_manager.read_file(encoded_file, file_extension)  
        if content is None:
            raise HTTPException(status_code=422, detail="Failed to process the file or unsupported file type")
        
        bibtex_manager = FastAPIBibtexManager(content, file_extension)
        # Creating the response
        temp_file_path = bibtex_manager.convert_and_download_bibtex()
        encoded_file = api_utils.file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = BibliographyResponse(encoded_bib=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response

    
@router.post("/search/v01/standalone/bibliography/", **lit_api_config.STANDALONE_BIBLIOGRAPHY_META)
async def bibliography_download(
    request: BibliographyRequest,
    background_tasks: BackgroundTasks
    ) -> BibliographyResponse:
    """
    Processes an uploaded file (either a DOCX or XLSX), converts the contained PMIDs to a BibTeX format,
    and returns the BibTeX bibliography as a base64 encoded string. This endpoint is ideal for users who need
    to quickly convert bibliographic data from documents into a format suitable for citation management tools.
    """
    file_bytes = base64.b64decode(request.file_encoded)
    response = get_bibtex_response(
        file_bytes,
        request.file_extension,
        background_tasks
        )
    return response