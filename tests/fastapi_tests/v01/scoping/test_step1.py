def test_search(client, perform_post_request, validate_encoded_response):
    """
    Tests the POST method for performing the first scoping review article search.
    """
    # URL for the POST request
    url = "/search/v01/scoping/step1/"

    # The payload containing the base64-encoded XLSX file
    payload = {"research_question": "post-surgical headache"}

    # Make the POST request
    response = perform_post_request(client, url, payload)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")
