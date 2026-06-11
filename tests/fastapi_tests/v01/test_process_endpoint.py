from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.server import app


# Helper: valid payload
def get_valid_payload():
    return {
        "research_question": "What are the ethical considerations in AI research?",
        "openai_compatible_endpoint": "https://example.com/v1/chat/completions",
        "openai_compatible_model": "gpt-4",
    }


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (get_valid_payload(), 200),
        # Missing endpoint
        ({**get_valid_payload(), "openai_compatible_endpoint": None}, 422),
        # Missing model
        ({**get_valid_payload(), "openai_compatible_model": None}, 422),
    ],
)
def test_process_endpoint_various_payloads(payload, expected_status):
    with patch("app.server.process_request") as mock_process:
        mock_process.return_value = {"message": "Request processed successfully"}
        client = TestClient(app)
        url = "/process"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer test-api-key",
        }
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == expected_status
        if response.status_code == 200:
            assert "application/json" in response.headers["content-type"]
            response_data = response.json()
            assert "message" in response_data
            assert response_data["message"] == "Request processed successfully"


def test_process_endpoint_missing_auth():
    payload = {
        "research_question": "What are the ethical considerations in AI research?",
        "openai_compatible_endpoint": "https://example.com/v1/chat/completions",
        "openai_compatible_model": "gpt-4",
    }
    with patch("app.server.process_request") as mock_process:
        mock_process.return_value = {"message": "Request processed successfully"}
        client = TestClient(app)
        url = "/process"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
            # No Authorization header
        }
        response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 422


def test_process_endpoint_invalid_key():
    payload = get_valid_payload()
    with patch("app.server.process_request") as mock_process:
        mock_process.side_effect = Exception("Invalid API Key")
        client = TestClient(app)
        url = "/process"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_key",
        }
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 500
        assert "Invalid API Key" in response.text
