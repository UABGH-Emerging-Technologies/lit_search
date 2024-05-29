from pydantic import BaseModel, Field
from app.v01.schemas import UploadableFiles


class BibliographyRequest(BaseModel):
    file_extension: UploadableFiles
    file_encoded: str = Field(..., description="Base64-encoded DOCX OR XLSX file content.")
    
class BibliographyResponse(BaseModel):
    encoded_bib: str = Field(..., description="Base64-encoded BIB file. Decode to obtain the BIB file.")