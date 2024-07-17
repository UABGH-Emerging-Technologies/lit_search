from fastapi import Form
from ScopingReview.Keywords.Manager import KeywordData
from fastapi import HTTPException
from pydantic import ValidationError
from typing import List, Tuple, Any

def validate_keywords_data(primary: List, secondary: List, exclusion: List) -> KeywordData:
    """
    The function `validate_keywords_data` takes three lists of keywords as input, constructs a data
    dictionary, validates it, and returns a `KeywordData` instance or raises a `HTTPException` with
    validation error details.
    
    Args:
      primary (List): List[str]
      secondary (List): Secondary keywords are additional keywords that are related to the primary
    keywords but are not as important. They provide additional context or information but are not the
    main focus.
      exclusion (List): The `exclusion` parameter in the `validate_keywords_data` function refers to a
    list of keywords that should be excluded from the primary and secondary keyword lists during
    validation. These keywords are not allowed to be present in the primary or secondary keyword lists.
    
    Returns:
      The function `validate_keywords_data` is returning an instance of `KeywordData` after validating
    the input data provided in the `primary`, `secondary`, and `exclusion` lists. If there is a
    validation error during the creation of the `KeywordData` instance, a `HTTPException` with status
    code 422 and details of the validation error will be raised.
    """
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