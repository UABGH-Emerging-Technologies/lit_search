def test_draft_summaries(
    client,
    categorized_xlsx,
    perform_post_request,
    validate_encoded_response
    ):
    """
    Tests the POST method for drafting a category summaries.
    """
    # URL for the POST request
    url = '/search/v01/scoping/step4/'
    
    # The payload containing the base64-encoded XLSX file
    payload = {
        "research_question": "post-surgical headache",
        "xlsx_encoded": categorized_xlsx
    }
    
    # Make the POST request
    response = perform_post_request(client, url, payload)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_docx")
