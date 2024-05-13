from pydantic import BaseModel


class SearchRequest(BaseModel):
    research_question: str
