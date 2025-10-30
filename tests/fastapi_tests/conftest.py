import json
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def load_secrets(secrets_dir="/workspaces/scopingreview/secrets"):
    """
    Load each file in the specified directory as an environment variable.
    The name of the environment variable is derived from the filename.
    """
    if os.path.exists(secrets_dir):
        for filename in os.listdir(secrets_dir):
            file_path = os.path.join(secrets_dir, filename)
            with open(file_path, "r") as secret_file:
                env_var_name = filename.replace(".txt", "")
                env_var_value = secret_file.read().strip()
                os.environ[env_var_name] = env_var_value


@pytest.fixture(scope="session", autouse=True)
def set_env_vars():
    """
    A fixture that automatically loads all secrets into environment variables.
    This fixture runs once per session and automatically before any tests are run.
    """
    load_secrets()


@pytest.fixture(autouse=True)
def mock_llm_calls():
    """
    Mock all LLM API calls to avoid making real requests during tests.
    """
    import json
    
    # Create a mock LLM interface that returns structured keyword data
    mock_llm = MagicMock()
    
    # Mock response for keyword extraction - returns JSON string as .content
    mock_keyword_response = MagicMock()
    keyword_json_string = json.dumps({
        "primary_keywords": ["headache", "surgery", "postoperative"],
        "secondary_keywords": ["pain", "anesthesia", "recovery"],
        "exclusion_keywords": ["pediatric", "animal"]
    })
    mock_keyword_response.content = keyword_json_string
    
    # For query generation, return a simple text query
    mock_query_response = MagicMock()
    mock_query_response.content = "(headache[Title/Abstract]) AND (surgery[Title/Abstract]) AND (postoperative[Title/Abstract])"
    
    # Configure the mock to return different responses based on what's being called
    def mock_invoke(prompt, *args, **kwargs):
        # Convert prompt to string for checking
        prompt_str = str(prompt)
        
        # If the prompt mentions extracting keywords or contains JSON structure hints
        if "extract" in prompt_str.lower() or "json" in prompt_str.lower() or "primary_keywords" in prompt_str:
            return mock_keyword_response
        else:
            # Default to query response for PubMed query generation
            return mock_query_response
    
    mock_llm.invoke.side_effect = mock_invoke
    
    # Define the replacement function for WorkflowHandler
    def mock_init_openai(self, openai_compatible_endpoint, openai_compatible_key, openai_compatible_model, name=None):
        self.llm_interface = mock_llm
        self.openai_compatible_endpoint = openai_compatible_endpoint
        self.openai_compatible_key = openai_compatible_key
        self.openai_compatible_model = openai_compatible_model
    
    with patch('aiweb_common.WorkflowHandler.WorkflowHandler._init_openai', new=mock_init_openai):
        yield mock_llm

@pytest.fixture
def client():
    """
    The function `client()` sets up a test client for interacting with a Flask application.
    """
    from app.server import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def uncategorized_xlsx():
    path_to_encoded_file = "tests/assets/uncategorized_xlsx.txt"
    with open(path_to_encoded_file, "r") as file:
        return file.read().strip()


@pytest.fixture
def category_summaries_docx():
    path_to_encoded_file = "tests/assets/category_summaries_docx.txt"
    with open(path_to_encoded_file, "r") as file:
        return file.read().strip()


@pytest.fixture
def categorized_xlsx():
    path_to_encoded_file = "tests/assets/categorized_xlsx_bytes.txt"
    with open(path_to_encoded_file, "r") as file:
        return file.read().strip()


@pytest.fixture
def validate_encoded_response():
    def validate(resp, expected_content_type, key):
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Response: {resp.text}"
        assert expected_content_type in resp.headers["content-type"]
        assert key in resp.json()
        assert len(resp.json()[key]) > 0
    return validate


@pytest.fixture
def perform_post_request():
    def do_post(client, url, data, headers=None):
        # Add required LLM config fields if not present
        if "openai_compatible_endpoint" not in data:
            data["openai_compatible_endpoint"] = "https://api.openai.com/v1/chat/completions"
        if "openai_compatible_model" not in data:
            data["openai_compatible_model"] = "gpt-4"
        
        # Set default headers with Authorization if not provided
        if headers is None:
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer test_api_key"
            }
        
        return client.post(url, content=json.dumps(data).encode("utf-8"), headers=headers)
    
    return do_post