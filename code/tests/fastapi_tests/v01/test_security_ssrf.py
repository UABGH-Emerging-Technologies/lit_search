import pytest

from app.v01.net_validators import validate_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/v1",
        "http://127.0.0.1:8000",
        "http://10.0.0.5/api",
        "http://192.168.1.10",
        "http://[::1]/x",
        "ftp://example.com/x",
        "not-a-url",
        "https:///nohost",
    ],
)
def test_validate_public_http_url_rejects_bad_urls(url: str):
    with pytest.raises(ValueError):
        validate_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/llm",
        "https://api.openai.com/v1/chat/completions",
    ],
)
def test_validate_public_http_url_accepts_public_urls(url: str):
    assert validate_public_http_url(url) == url


def test_summary_endpoint_rejects_private_endpoint(client, perform_post_request):
    data = {
        "research_question": "x",
        "openai_compatible_endpoint": "http://169.254.169.254/",
        "openai_compatible_model": "gpt-4",
    }
    response = perform_post_request(client, "/v01/standalone/summary/", data)
    assert response.status_code == 422
