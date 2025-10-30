from pydantic import BaseModel, Field, field_validator
from app.v01.schemas import UploadableFiles
from app.v01.validators import validate_docx_bytes, validate_xlsx_bytes


class BibliographyRequest(BaseModel):
    file_extension: UploadableFiles
    file_encoded: str = Field(..., description="Base64-encoded DOCX OR XLSX file content.")


    @field_validator("file_encoded")
    @classmethod
    def check_cv_mime_type(cls, v, values, **kwargs):
        """
        The function `check_cv_mime_type` attempts to validate a file's content as either a DOCX or XLSX
        format and raises a ValueError if both validations fail.

        Args:
          cls: In the provided code snippet, the `check_cv_mime_type` method seems to be a class method as
        it takes `cls` as the first parameter. In Python, `cls` conventionally represents the class itself
        within a class method.
          v: It looks like the code you provided is a method for checking the MIME type of a file content.
        The method first tries to validate the content as a DOCX file using the `validate_docx_bytes`
        function. If that validation fails, it then tries to validate the content as an XLSX

        Returns:
          The `check_cv_mime_type` method is returning the result of validating the input `v` as either a
        DOCX or XLSX file. If the validation as DOCX fails, it will try to validate it as XLSX. If both
        validations fail, it will raise a `ValueError` with a message indicating that the file content must
        be either a valid DOCX or XLS
        """
        try:
            # First try validating as DOCX
            return validate_docx_bytes(cls, v, values)
        except ValueError as e1:
            # If DOCX validation fails, try XLSX
            try:
                return validate_xlsx_bytes(cls, v, values)
            except ValueError as e2:
                # If both validations fail, raise a ValueError
                raise ValueError(
                    f"File content must be either a valid DOCX or XLSX. Errors: {e1}; {e2}"
                ) from e2


class BibliographyResponse(BaseModel):
    encoded_bib: str = Field(
        ..., description="Base64-encoded BIB file. Decode to obtain the BIB file."
    )
