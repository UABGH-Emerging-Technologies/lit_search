
from pydantic import Field, field_validator
from app.v01.validators import validate_xlsx_bytes
from app.v01.schemas import SearchRequest
from typing import List
from fastapi import Form


class KeywordsRequest(SearchRequest):
    xlsx_encoded: str = Field(..., description="Base64-encoded XLSX file content.")
    
    @field_validator('xlsx_encoded')
    @classmethod
    def check_mime_type(cls, v, values, **kwargs):
        """
        The function `check_mime_type` validates XLSX file bytes.
        
        Args:
          cls: In the provided code snippet, the `cls` parameter is typically used to refer to the class
        itself within a class method. It is a common convention in Python to use `cls` as the first
        parameter in class methods to represent the class object.
          v: The `v` parameter in the `check_mime_type` function likely represents the value that needs
        to be validated or checked for its MIME type. It is passed as an argument to the function when
        it is called.
          values: The `values` parameter typically refers to a dictionary containing all the values
        being passed to the function or method. In this context, it is likely used to pass additional
        information or context to the `check_mime_type` function.
        
        Returns:
          The `check_mime_type` function is returning the result of calling the `validate_xlsx_bytes`
        function with the arguments `cls`, `v`, and `values`.
        """
        return validate_xlsx_bytes(cls, v, values)


class IterationRequest(KeywordsRequest):
    primary_keywords: List[str] = Form(...)
    secondary_keywords: List[str] = Form(...)
    exclusion_keywords: List[str] = Form(...)
