from pydantic import BaseModel, Field
from typing import List

class KeywordsData(BaseModel):
    primary_keywords: List[str] = Field(..., example=["keyword1", "keyword2"], description="List of primary keywords")
    secondary_keywords: List[str] = Field(..., example=["keyword3", "keyword4"], description="List of secondary keywords")
    exclusion_keywords: List[str] = Field(..., example=["keyword5"], description="List of exclusion keywords")


def parse_keywords(content):
    # Load the JSON string into a Python dictionary
    data = json.loads(content)

    # Extract keyword lists into variables
    primary_keywords = data.get("Primary Keywords", [])
    secondary_keywords = data.get("Secondary Keywords", [])
    exclusion_keywords = data.get("Exclusion Keywords", [])

    return primary_keywords, secondary_keywords, exclusion_keywords