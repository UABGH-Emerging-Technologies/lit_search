from pydantic import BaseModel, Field, field_validator

from app.v01.schemas import SearchRequest, XLSXinRequest
from app.v01.validators import validate_docx_bytes


class CategoriesRequest(SearchRequest, XLSXinRequest):
    """
    Request schema for categorizing articles.
    Combines search parameters with xlsx file input.
    """

    user_defined_categories: str


class SummariesRequest(SearchRequest, XLSXinRequest):
    """
    Request schema for generating summaries.
    Combines search parameters with xlsx file input.
    """

    pass


class DraftRequest(SearchRequest):
    """
    Request schema for drafting a review article.
    Requires a DOCX file instead of XLSX.
    """

    docx_encoded: str = Field(..., description="Base64-encoded DOCX file.")

    @field_validator("docx_encoded")
    @classmethod
    def check_mime_type(cls, v, values, **kwargs):
        """
        Validates DOCX file to ensure proper MIME type.
        """
        return validate_docx_bytes(cls, v, values)
