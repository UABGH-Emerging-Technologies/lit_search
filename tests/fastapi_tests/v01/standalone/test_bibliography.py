import pytest


@pytest.fixture
def file_content(request, category_summaries_docx, uncategorized_xlsx):
    """Dynamically returns the correct file content based on the test parameter."""
    if request.param == ".docx":
        return category_summaries_docx
    elif request.param == ".xlsx":
        return uncategorized_xlsx
    else:
        raise ValueError("Unsupported file extension")


@pytest.mark.parametrize(
    "file_extension, file_content",
    [
        (".docx", ".docx"),  # Pass the file extension as a parameter to the fixture
        (".xlsx", ".xlsx"),
    ],
    indirect=["file_content"],
)  # Now only file_content is indirect
def test_bibtex_generation(
    client,
    perform_post_request,
    validate_encoded_response,
    file_extension,
    file_content,  # This now uses the custom fixture
):
    """
    Tests the POST method for creating the first draft of a scoping review article
    """
    url = "/search/v01/standalone/bibliography/"
    # Endpoint/model/key required by API for every request
    payload = {
        "file_extension": file_extension,
        "file_encoded": file_content,
        "openai_compatible_endpoint": "https://example.com/llm",
        "openai_compatible_model": "test-model"
    }
    headers = {"Authorization": "Bearer test-key"}
    # Endpoint/model/key required by API for every request
    response = perform_post_request(client, url, payload, headers)
    validate_encoded_response(response, "application/json", "encoded_bib")
