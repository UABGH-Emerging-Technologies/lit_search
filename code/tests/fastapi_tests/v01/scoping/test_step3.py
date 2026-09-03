def test_categorize(client, uncategorized_xlsx, perform_post_request, validate_encoded_response):
    """
    Tests the POST method for assigning categories to articles.
    """
    # URL for the POST request
    url = "/v01/scoping/step3/"

    # The payload containing the base64-encoded XLSX file
    # Endpoint/model/key required by API for every request
    payload = {
        "research_question": "post-surgical headache",
        "user_defined_categories": "marfan, mri, spinal headache",
        "xlsx_encoded": uncategorized_xlsx,
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model",
    }
    headers = {"Authorization": "Bearer test-key"}
    # Endpoint/model/key required by API for every request
    response = perform_post_request(client, url, payload, headers)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")
