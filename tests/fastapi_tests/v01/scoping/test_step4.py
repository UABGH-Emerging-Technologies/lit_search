def test_draft_summaries(client, categorized_xlsx, perform_post_request, validate_encoded_response):
    """
    Tests the POST method for drafting a category summaries.
    """
    # URL for the POST request
    url = "/v01/scoping/step4/"

    # The payload containing the base64-encoded XLSX file
    # Endpoint/model/key required by API for every request
    payload = {
        "research_question": "post-surgical headache",
        "xlsx_encoded": categorized_xlsx,
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model",
    }
    headers = {"Authorization": "Bearer test-key"}
    # Endpoint/model/key required by API for every request
    response = perform_post_request(client, url, payload, headers)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_docx")
