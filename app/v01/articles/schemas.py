from pydantic import BaseModel
from enum import Enum


class SearchRequest(BaseModel):
    research_question: str
