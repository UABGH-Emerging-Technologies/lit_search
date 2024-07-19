from typing import List

from fastapi import Form

from app.v01.schemas import SearchRequest, XLSXinRequest


class KeywordsRequest(SearchRequest, XLSXinRequest):
    """This class extends the KeywordsRequest class to handle iteration requests."""

    pass


class IterationRequest(KeywordsRequest):
    """This class inherits from both SearchRequest and XLSXinRequest classes."""

    primary_keywords: List[str] = Form(...)
    secondary_keywords: List[str] = Form(...)
    exclusion_keywords: List[str] = Form(...)
