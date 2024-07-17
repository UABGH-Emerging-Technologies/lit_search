def test_categorize(
    client,
    uncategorized_xlsx,
    perform_post_request,
    validate_encoded_response
    ):
    """
    Tests the POST method for assigning categories to articles.
    """
    # URL for the POST request
    url = '/search/v01/scoping/step3/'
    
    # The payload containing the base64-encoded XLSX file
    payload = {
        "user_defined_categories": "marfan, mri, spinal headache",
        "xlsx_encoded": uncategorized_xlsx
    }
    
    # Make the POST request
    response = perform_post_request(client, url, payload)
    # Assertions to verify the response status and content
    validate_encoded_response(response, "application/json", "encoded_xlsx")
