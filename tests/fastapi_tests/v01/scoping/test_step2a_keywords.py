def test_keyword_extraction(
    client,
    uncategorized_xlsx,
    perform_post_request,
):
    """
    Tests the POST method for extracting (really abstracting) search keywords.
    """
    # URL for the POST request
    url = "/v01/scoping/step2/keywords/"

    # The payload containing the base64-encoded XLSX file
    # Endpoint/model/key required by API for every request
    payload = {
        "research_question": "post-surgical headache",
        "xlsx_encoded": uncategorized_xlsx,
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model"
    }
    headers = {"Authorization": "Bearer test-key"}
    # Endpoint/model/key required by API for every request
    response = perform_post_request(client, url, payload, headers)

    # Assertions to verify the response status and content
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = (
        response.json()
    )  # This assumes that 'response' is an object with a method json() that parses the JSON response.

    # Check for the existence of keyword categories in the response
    assert "primary_keywords" in data, "Response JSON should include 'primary_keywords'"
    assert "secondary_keywords" in data, "Response JSON should include 'secondary_keywords'"
    assert "exclusion_keywords" in data, "Response JSON should include 'exclusion_keywords'"

    # Validate that each keyword list is correct in terms of content and type
    assert isinstance(data["primary_keywords"], list), "'primary_keywords' should be a list"
    assert isinstance(data["secondary_keywords"], list), "'secondary_keywords' should be a list"
    assert isinstance(data["exclusion_keywords"], list), "'exclusion_keywords' should be a list"
