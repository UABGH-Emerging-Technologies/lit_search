import base64
import os
from aiweb_common.file_operations.file_handling import file_to_base64
from aiweb_common.file_operations.upload_manager import FastAPIUploadManager
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
import app.fastapi_config as api_config
from app.v01.schemas import UploadableFiles
from app.v01.standalone.schemas import BibliographyRequest, BibliographyResponse
from ScopingReview.Bibliography.Manager import FastAPIBibtexManager
from app.dependencies import security, get_api_key

router = APIRouter(tags=["standalone", "bibliography"])


def get_bibtex_response(
    encoded_file: str, file_extension: UploadableFiles, background_tasks: BackgroundTasks
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
        upload_manager = FastAPIUploadManager(background_tasks)
        # Handles both .docx and .xlsx files
        content = upload_manager.read_and_validate_file(encoded_file, file_extension)
        if content is None:
            raise HTTPException(
                status_code=422, detail="Failed to process the file or unsupported file type"
            )

        bibtex_manager = FastAPIBibtexManager(content, file_extension)
        # Creating the response
        # TODO: this should return an object, not a path
        temp_file_path = bibtex_manager.convert_and_download_bibtex()
        encoded_file = file_to_base64(temp_file_path)  # Convert the file to a base64 string
        background_tasks.add_task(os.unlink, temp_file_path)
        response = BibliographyResponse(encoded_bib=encoded_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return response


@router.post("/search/v01/standalone/bibliography/", **api_config.STANDALONE_BIBLIOGRAPHY_META)
async def bibliography_download(
    request: BibliographyRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> BibliographyResponse:
    """
    Processes uploaded file and converts to BibTeX format.
    Requires API key in Authorization header (Bearer scheme).
    """
    api_key = await get_api_key(credentials)
    
    response = get_bibtex_response(
        request.file_encoded,
        request.file_extension,
        background_tasks,
    )
    return response
