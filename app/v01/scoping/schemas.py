
from app.v01.schemas import SearchRequest, XLSXinRequest
from app.v01.validators import validate_docx_bytes
# for consistency with our other apis, don't delete this import.
# Other modules import Keywords Data from this file.
from ScopingReview.search import KeywordsData
from pydantic import Field, field_validator


class CategoriesRequest(XLSXinRequest):
    user_defined_categories: str

class SummariesRequest(SearchRequest, XLSXinRequest):
    pass

class DraftRequest(SearchRequest):
    docx_encoded: str = Field(..., description="Base64-encoded DOCX file.")
    
    @field_validator('docx_encoded')
    @classmethod
    def check_mime_type(cls, v, values, **kwargs):
        """
        The function `check_mime_type` validates a DOCX file by checking its MIME type.
        
        Args:
          cls: In the given code snippet, the parameter `cls` typically stands for the class itself. It is a
        common convention in Python to use `cls` as the first parameter in class methods to refer to the
        class itself. This parameter allows the method to access class-level attributes and methods.
          v: The `v` parameter in the `check_mime_type` method likely represents the value that needs to be
        validated or checked for its MIME type. It is a variable that holds the data (such as a file or
        content) whose MIME type needs to be verified.
          values: The `values` parameter typically refers to a dictionary containing the values of the
        request parameters or data being passed to a function or method. In the context of the
        `check_mime_type` method, the `values` parameter likely contains additional data related to the MIME
        type validation process.
        
        Returns:
          The `validate_docx_bytes` function is being called with the arguments `cls, v, values`, and the
        result of this function call is being returned.
        """
        return validate_docx_bytes(cls, v, values)
