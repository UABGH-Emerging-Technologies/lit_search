from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.v01.validators import validate_xlsx_bytes


class UploadableFiles(str, Enum):
    """The class `UploadableFiles` is a subclass of `str` and `Enum` in Python."""

    DOCX = ".docx"
    XLSX = ".xlsx"


class SearchRequest(BaseModel):
    """
    This class represents a search request.
    Note: API key comes from Authorization header, not request body.
    """

    research_question: str
    openai_compatible_endpoint: str = Field(..., description="OpenAI-compatible endpoint URL")
    openai_compatible_model: str = Field(..., description="Model name to use for LLM calls")
    # Note: openai_compatible_key comes from Authorization header


class MSWordResponse(BaseModel):
    """This class represents a response containing a Microsoft Word document."""

    encoded_docx: str = Field(
        ...,
        json_schema_extra={
            "description": "Base64-encoded DOCX file. Decode to obtain the DOCX file."
        },
    )


class BibTexResponse(BaseModel):
    """This class represents a response in BibTeX format."""

    encoded_bib: str = Field(
        ...,
        json_schema_extra={
            "description": "Base64-encoded BIB file. Decode to obtain the BIB file."
        },
    )


class MSExcelResponse(BaseModel):
    """This class represents a response containing a Microsoft Excel file."""

    encoded_xlsx: str = Field(
        ...,
        json_schema_extra={
            "description": "Base64-encoded XLSX file. Decode to obtain the XLSX file."
        },
    )


class XLSXinRequest(BaseModel):
    """This class represents a request object for handling XLSX file data."""

    xlsx_encoded: str = Field(..., description="Base64-encoded XLSX file content.")

    @field_validator("xlsx_encoded")
    @classmethod
    def check_mime_type(cls, v, values, **kwargs):
        """
        Validates XLSX file bytes to ensure proper MIME type.
        """
        return validate_xlsx_bytes(cls, v, values)
