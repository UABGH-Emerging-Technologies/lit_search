import json
import pytest
import io
import base64


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
    
    # Decode base64 string to bytes for file upload
    file_bytes = base64.b64decode(uncategorized_xlsx)
    
    # Prepare multipart form data
    files = {
        "file": ("test.xlsx", io.BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    
    # Prepare form fields (comma-separated strings)
    data = {
        "research_question": "post-surgical headache",
        "primary_keywords": ",".join(keyword_data["primary_keywords"]),
        "secondary_keywords": ",".join(keyword_data["secondary_keywords"]),
        "exclusion_keywords": ",".join(keyword_data["exclusion_keywords"]),
        "openai_compatible_endpoint": "https://api.openai.com/v1/chat/completions",  
        "openai_compatible_model": "gpt-4",
    }
    
    # Headers with authorization
    headers = {
        "Authorization": "Bearer test_api_key"
    }
    
    # Make the POST request with multipart form data
    # NOTE: Don't use perform_post_request fixture - it's for JSON only
    response = client.post(url, data=data, files=files, headers=headers)
    
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")