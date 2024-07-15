from app.v01.schemas import SearchRequest, XLSXinRequest
from typing import List
from fastapi import Form


class KeywordsRequest(SearchRequest, XLSXinRequest):
  pass

class IterationRequest(KeywordsRequest):
    primary_keywords: List[str] = Form(...)
    secondary_keywords: List[str] = Form(...)
    exclusion_keywords: List[str] = Form(...)
