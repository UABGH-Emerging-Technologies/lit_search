def test_summary_writing(client, perform_post_request, validate_encoded_response):
    """
    Tests the POST method for creating the first draft of a scoping review article
    """
    # URL for the POST request
    url = "/search/v01/standalone/summary/"

    # The payload containing the base64-encoded DOCX file
    payload = {
        "research_question": "post-surgical headache",
    }

    # Make the POST request
    response = perform_post_request(client, url, payload)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_docx")
