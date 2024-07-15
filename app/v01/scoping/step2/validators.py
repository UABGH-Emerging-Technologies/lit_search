from fastapi import Form
from ScopingReview.Keywords.Manager import KeywordData
from fastapi import HTTPException
from pydantic import ValidationError
from typing import List, Tuple, Any

def validate_keywords_data(primary: List, secondary: List, exclusion: List) -> KeywordData:
    # Construct data dictionary from form fields
    data = {
        "primary_keywords": primary,
        "secondary_keywords": secondary,
        "exclusion_keywords": exclusion
    }

    try:
        # Validate and create KeywordsData instance
        return KeywordData(**data)
    except ValidationError as e:
        # Handle validation errors
        raise HTTPException(status_code=422, detail={"error": "Validation failed", "details": e.errors()})