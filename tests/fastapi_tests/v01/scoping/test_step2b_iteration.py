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
    
    # Prepare form fields (comma-separated strings)
    data = {
        "research_question": "post-surgical headache",
        "primary_keywords": ",".join(keyword_data["primary_keywords"]),
        "secondary_keywords": ",".join(keyword_data["secondary_keywords"]),
        "exclusion_keywords": ",".join(keyword_data["exclusion_keywords"]),
        "xlsx_encoded": uncategorized_xlsx,
        # Endpoint/model required by API for every request
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model",
    }
    
    # Headers with authorization
    # Authorization header required by API for every request
    headers = {
        "Authorization": "Bearer test-key"
    }
    
    # Make the POST request with multipart form data
    # NOTE: Don't use perform_post_request fixture - it's for JSON only
    response = client.post(url, data=data, headers=headers)
    
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")
