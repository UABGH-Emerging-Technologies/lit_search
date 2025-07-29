import json

import pytest


@pytest.fixture
def keyword_data():
    """Load keywords from a JSON file."""
    with open("tests/assets/keywords.txt", "r") as file:
        data = json.load(file)
    return data


def test_iteration(
    client, uncategorized_xlsx, keyword_data, perform_post_request, validate_encoded_response
):
    """
    Tests the POST method for iterating on a scoping review article search.
    """
    # URL for the POST request
    url = "/search/v01/scoping/step2/iteration/"

    # The payload containing the base64-encoded XLSX file
    payload = {
        "research_question": "post-surgical headache",
        "xlsx_encoded": uncategorized_xlsx,
        "primary_keywords": keyword_data["primary_keywords"],
        "secondary_keywords": keyword_data["secondary_keywords"],
        "exclusion_keywords": keyword_data["exclusion_keywords"],
    }

    # Make the POST request
    response = perform_post_request(client, url, payload)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")
