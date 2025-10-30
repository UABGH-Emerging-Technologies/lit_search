def test_draft_article(
    client, category_summaries_docx, perform_post_request, validate_encoded_response
):
    """
    Tests the POST method for creating the first draft of a scoping review article
    """
    # URL for the POST request
    url = "/search/v01/scoping/step5/"

    # The payload containing the base64-encoded DOCX file
    # Endpoint/model/key required by API for every request
    payload = {
        "research_question": "post-surgical headache",
        "docx_encoded": category_summaries_docx,
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model"
    }
    headers = {"Authorization": "Bearer test-key"}
    # Endpoint/model/key required by API for every request
    response = perform_post_request(client, url, payload, headers)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_docx")
