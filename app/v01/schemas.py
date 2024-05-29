from pydantic import BaseModel, Field
from enum import Enum


class UploadableFiles(str, Enum):
    DOCX = ".docx"
    XLSX = ".xlsx"
    

class SearchRequest(BaseModel):
    research_question: str


class MSWordResponse(BaseModel):
    encoded_docx: str = Field(..., description="Base64-encoded DOCX file. Decode to obtain the DOCX file.")


class BibTexResponse(BaseModel):
    encoded_docx: str = Field(..., description="Base64-encoded BIB file. Decode to obtain the BIB file.")