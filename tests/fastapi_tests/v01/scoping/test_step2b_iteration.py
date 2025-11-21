import json
import pytest

@pytest.fixture
def keyword_data():
    """Load keywords from a JSON file."""
    with open("tests/assets/keywords.txt", "r") as file:
        data = json.load(file)
    return data

def test_iteration(
    client, uncategorized_xlsx, keyword_data, validate_encoded_response
):
    """
    Tests the POST method for iterating on a scoping review article search.
    """
    # URL for the POST request
    url = "/search/v01/scoping/step2/iteration/"
    
    # Prepare JSON payload (lists instead of comma-separated strings)
    payload = {
        "research_question": "post-surgical headache",
        "primary_keywords": keyword_data["primary_keywords"],  # ← Changed to list
        "secondary_keywords": keyword_data["secondary_keywords"],  # ← Changed to list
        "exclusion_keywords": keyword_data["exclusion_keywords"],  # ← Changed to list
        "xlsx_encoded": uncategorized_xlsx,
        # Endpoint/model required by API for every request
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model",
    }
    
    # Headers with authorization
    headers = {
        "Authorization": "Bearer test-key"
    }
    
    # Make the POST request with JSON body (not form data)
    response = client.post(url, json=payload, headers=headers)  # ← Changed data= to json=
    
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")