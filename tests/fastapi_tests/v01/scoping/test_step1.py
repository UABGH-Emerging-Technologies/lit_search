import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.server import app
from app.v01.schemas import MSExcelResponse

# Helper: valid payload
def get_valid_payload():
    return {
        "research_question": "post-surgical headache",
        "openai_compatible_endpoint": "https://api.openai.com/v1/engines/davinci-codex/completions",
        "openai_compatible_model": "davinci-codex"
    }

@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (get_valid_payload(), 200),
        # Missing endpoint
        ({**get_valid_payload(), "openai_compatible_endpoint": None}, 422),
        # Missing model
        ({**get_valid_payload(), "openai_compatible_model": None}, 422),
    ]
)
def test_search_various_payloads(payload, expected_status):
    with patch("app.v01.scoping.step1.get_step1_response") as mock_response:
        mock_response.return_value = MSExcelResponse(encoded_xlsx="mocked_excel_data")
        client = TestClient(app)
        url = "/search/v01/scoping/step1/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key"
        }
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == expected_status


def test_search_missing_auth():
    payload = get_valid_payload()
    with patch("app.v01.scoping.step1.get_step1_response") as mock_response:
        mock_response.return_value = MSExcelResponse(encoded_xlsx="mocked_excel_data")
        client = TestClient(app)
        url = "/search/v01/scoping/step1/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
            # No Authorization header
        }
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 403


def test_search_invalid_key():
    payload = get_valid_payload()
    with patch("app.v01.scoping.step1.get_step1_response") as mock_response:
        mock_response.side_effect = Exception("Invalid API Key")
        client = TestClient(app)
        url = "/search/v01/scoping/step1/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_key"
        }
        
        # TestClient raises the exception, so we catch it
        with pytest.raises(Exception) as exc_info:
            response = client.post(url, headers=headers, json=payload)
        
        # Verify the exception message
        assert str(exc_info.value) == "Invalid API Key"