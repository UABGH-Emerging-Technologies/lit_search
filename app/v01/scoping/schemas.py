
from app.v01.schemas import SearchRequest, XLSXinRequest
from typing import List
from fastapi import Form
# for consistency with our other apis, don't delete this import.
# Other modules import Keywords Data from this file.
from ScopingReview.search import KeywordsData


class CategoriesRequest(XLSXinRequest):
    user_defined_categories: str

class SummariesRequest(SearchRequest, XLSXinRequest):
    pass