import json
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def load_secrets(secrets_dir="/workspaces/scopingreview/secrets"):
    """
    NO-OP in test context: Prevents loading any real secrets from the filesystem.
    This disables environment variable setting from secrets during test discovery.
    """
    pass  # Do not load secrets or set env vars in tests


@pytest.fixture(scope="session", autouse=True)
def set_env_vars():
    """
    A fixture that automatically loads all secrets into environment variables.
    This fixture runs once per session and automatically before any tests are run.
    """
    load_secrets()


@pytest.fixture(autouse=True)
def mock_external_calls(monkeypatch):
    """
    Mock all LLM, PromptyHandler, RAGResponseHandler, and token/encoding helpers to avoid real network/API calls.
    Also patch ScopingReview_config and app_config keys to avoid AttributeError during import.
    """
    import json
    from types import SimpleNamespace

    # --- Helper classes ---
    # Richer mock result object for LLM responses
    class MockResultObj:
        """
        Mocks LLM result object for tests.
        - .content: string response
        - .total_cost: attribute for cost tracking
        - dict-like access for code paths expecting dicts
        """
        def __init__(self, content, total_cost=0.0):
            self.content = content
            self.total_cost = total_cost
        def __getitem__(self, key):
            # Allow dict-like access for code paths expecting result['content']
            if key == "content":
                return self.content
            if key == "total_cost":
                return self.total_cost
            raise KeyError(key)
        def get(self, key, default=None):
            # Support .get() for dict-like code paths
            if key == "content":
                return self.content
            if key == "total_cost":
                return self.total_cost
            return default

    class DummyDataFrame:
        """
        Minimal pandas-like object for .iterrows() support in tests.
        Wraps a list of dicts and yields (index, row_dict) pairs.
        """
        def __init__(self, rows):
            self._rows = rows
        def iterrows(self):
            for idx, row in enumerate(self._rows):
                yield idx, row
        def __getitem__(self, key):
            # Support df["PMID"], df["Relevant"], etc.
            return [row.get(key) for row in self._rows]
        def dropna(self, subset=None):
            # Simulate dropna for subset of columns
            if subset is None:
                return self
            filtered = [row for row in self._rows if all(row.get(col) is not None for col in subset)]
            return DummyDataFrame(filtered)
        def apply(self, func, axis=1):
            # Simulate apply for relevance check
            return [func(row) for row in self._rows]
        def astype(self, dtype):
            # Simulate astype for columns
            return self
        def merge(self, other, on, how):
            # Simulate merge for test purposes
            return self
        @property
        def columns(self):
            # Return all keys present in any row
            keys = set()
            for row in self._rows:
                keys.update(row.keys())
            return list(keys)

    class MockAugService:
        def retrieve_data(self, prompt, *args, **kwargs):
            # Return DummyDataFrame with all columns needed for test workflows
            docs = [
                {
                    "title": "Mocked Article 1",
                    "content": "Some content",
                    "id": 1,
                    "PMID": "12345",
                    "Relevant": True,
                    "keywords": "headache,surgery,therapy",
                    "citation": "Smith et al. (2020)",
                    "abstract": "This is a mocked abstract.",
                },
                {
                    "title": "Mocked Article 2",
                    "content": "Other content",
                    "id": 2,
                    "PMID": "67890",
                    "Relevant": False,
                    "keywords": "asthma,colitis",
                    "citation": "Doe et al. (2021)",
                    "abstract": "Another mocked abstract.",
                }
            ]
            return DummyDataFrame(docs)

    class MockRAGResponseHandler:
        def __init__(self, *args, **kwargs):
            self.aug_service = MockAugService()

    # --- Mock PromptyHandler.generate_response ---
    def mock_generate_response(self, chain, input_data):
        # Return tuple (result_obj, result_meta)
        # Richer mock needed for code paths that expect .content, .total_cost, and dict-like access
        result_obj = MockResultObj("Mocked LLM response content", total_cost=0.0)
        # result_meta must be dict-like with at least "total_cost"
        result_meta = {"total_cost": 0.0, "model": "mock-llm"}
        return result_obj, result_meta
    # Patch PromptyHandler.generate_response to return (MockResultObj, result_meta)
    monkeypatch.setattr("aiweb_common.generate.PromptyHandler.generate_response", mock_generate_response, raising=False)

    # --- Mock RAGResponseHandler ---
    # Patch AugmentedResponse.RAGResponseHandler to use deterministic MockAugService
    monkeypatch.setattr("aiweb_common.generate.AugmentedResponse.RAGResponseHandler", MockRAGResponseHandler, raising=False)

    # --- Mock LLM factories if present ---
    def mock_llm_factory(*args, **kwargs):
        class MockLLM:
            def invoke(self, prompt, *a, **kw):
                return MockResultObj("Mocked LLM invoke response")
            def __call__(self, *a, **kw):
                return MockResultObj("Mocked LLM __call__ response")
            def chat(self, *a, **kw):
                return MockResultObj("Mocked LLM chat response")
        return MockLLM()
    # Patch all ChatOpenAI factories/classes to mock_llm_factory
    monkeypatch.setattr("ScopingReview_config.config.ChatOpenAI", mock_llm_factory, raising=False)
    monkeypatch.setattr("ScopingReview_config.ChatOpenAI", mock_llm_factory, raising=False)
    monkeypatch.setattr("aiweb_common.generate.ChatOpenAI", mock_llm_factory, raising=False)

    # --- Defensive app_config placeholders ---
    # Patch GPT4_KEY and OPENAI_API_KEY if missing
    # Patch GPT4_KEY and OPENAI_API_KEY to dummy values if missing
    try:
        import ScopingReview_config.app_config as app_config
        if not hasattr(app_config, "GPT4_KEY"):
            monkeypatch.setattr(app_config, "GPT4_KEY", "test-key", raising=False)
        if not hasattr(app_config, "OPENAI_API_KEY"):
            monkeypatch.setattr(app_config, "OPENAI_API_KEY", "test-key", raising=False)
    except Exception:
        # If import fails, patch at module path
        monkeypatch.setattr("ScopingReview_config.app_config.GPT4_KEY", "test-key", raising=False)
        monkeypatch.setattr("ScopingReview_config.app_config.OPENAI_API_KEY", "test-key", raising=False)

    # --- Mock tiktoken.encoding_for_model ---
    class DummyEncoding:
        def encode(self, text):
            return [1, 2, 3]
        def decode(self, tokens):
            return "decoded"
    # Patch tiktoken.encoding_for_model to return DummyEncoding
    monkeypatch.setattr("tiktoken.encoding_for_model", lambda *a, **k: DummyEncoding(), raising=False)

    # --- Patch aiweb_common.WorkflowHandler.WorkflowHandler._init_openai for legacy coverage ---
    # Patch WorkflowHandler._init_openai to assign a lightweight mock LLM interface and request attributes
    def mock_init_openai(self, openai_compatible_endpoint, openai_compatible_key, openai_compatible_model, name=None, use_responses_api=False, reasoning_effort=None):
        # Assign a mock LLM interface so workflows expecting self.llm_interface do not fail
        class MockLLM:
            def invoke(self, prompt, *a, **kw):
                class MockResultObj:
                    def __init__(self, content):
                        self.content = content
                return MockResultObj("Mocked LLM invoke response")
            def __call__(self, *a, **kw):
                class MockResultObj:
                    def __init__(self, content):
                        self.content = content
                return MockResultObj("Mocked LLM __call__ response")
            def chat(self, *a, **kw):
                class MockResultObj:
                    def __init__(self, content):
                        self.content = content
                return MockResultObj("Mocked LLM chat response")
        self.llm_interface = MockLLM()
        # Also assign endpoint/model/key attributes for workflows that expect them
        self.openai_compatible_endpoint = openai_compatible_endpoint
        self.openai_compatible_key = openai_compatible_key
        self.openai_compatible_model = openai_compatible_model
        if name is not None:
            self.name = name
    monkeypatch.setattr("aiweb_common.WorkflowHandler.WorkflowHandler._init_openai", mock_init_openai, raising=False)

    yield

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
        
        return client.post(url, json=data, headers=headers)
    
    return do_post

# --- Summary of external targets mocked in this test suite ---
# - aiweb_common.generate.PromptyHandler.generate_response
# - aiweb_common.generate.AugmentedResponse.RAGResponseHandler
# - aiweb_common.generate.ChatOpenAI
# - ScopingReview_config.config.ChatOpenAI
# - ScopingReview_config.ChatOpenAI
# - tiktoken.encoding_for_model
# - aiweb_common.WorkflowHandler.WorkflowHandler._init_openai
# - ScopingReview_config.app_config.GPT4_KEY
# - ScopingReview_config.app_config.OPENAI_API_KEY
# - load_secrets (NO-OP in test context)