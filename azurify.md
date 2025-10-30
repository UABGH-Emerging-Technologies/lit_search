## API Request Requirements

The API now requires the following fields in every request:

- `openai_compatible_endpoint`: The full URL of the OpenAI-compatible API endpoint to use for LLM calls.
- `openai_compatible_model`: The model name to use for the LLM.

The API key for authenticating with the OpenAI-compatible endpoint must be provided in the `Authorization` header using the Bearer scheme:

```
Authorization: Bearer <api_key>
```

All required fields must be provided by the client for every request. There is no fallback to configuration or secrets. This ensures full flexibility and clarity for multi-tenant or custom endpoint scenarios.

### Updated API Requirements
- The API now requires the following fields in every request:
  - `openai_compatible_endpoint`: The full URL of the OpenAI-compatible API endpoint to use for LLM calls.
  - `openai_compatible_model`: The model name to use for the LLM.
- The API key for authenticating with the OpenAI-compatible endpoint must be provided in the `Authorization` header using the Bearer scheme:
  ```
  Authorization: Bearer <api_key>
  ```
- All required fields must be provided by the client for every request. There is no fallback to configuration or secrets. This ensures full flexibility and clarity for multi-tenant or custom endpoint scenarios.
# Refactoring for Azure OpenAI Compatibility

This document outlines the changes made to the Data Feasibility API to support dynamic configuration of the LLM API key and model name through the API request. This allows for greater flexibility, particularly when using services like Azure OpenAI.

## Summary of Changes

The refactoring involved modifications to four key files:

1.  **`app/v01/schemas.py`**: The request model was updated to accept the new parameters.
2.  **`app/v01/idea.py`**: The API endpoint was updated to handle the new parameters.
3.  **`DataFeasibility/workflows.py`**: The core workflow was updated to dynamically instantiate the `ChatOpenAI` model.
4.  **`DataFeasibility/workflow_factory.py`**: The workflow factory was updated to pass the new parameters to the workflow constructors.
5.  **`DataFeasibilityConfig/config.py`**: The static `CHAT` object was removed.
6.  **`tests/fastapi_tests/test_api.py`**: The tests were updated to reflect the mandatory nature of the new fields.

## Detailed Changes

### 1. `app/v01/schemas.py`

The `FeasibilityRequest` model was updated to remove the API key field. The API key is now provided via the Authorization header.

```python
from pydantic import BaseModel

from DataFeasibility.workflow_factory import DatabaseName

class FeasibilityRequest(BaseModel):
    query: str
    source: DatabaseName
    openai_compatible_endpoint: str
    openai_compatible_model: str

class FeasibilityResponse(BaseModel):
    content: str
```

### 2. `app/v01/idea.py`

The `evaluate_idea` endpoint and the `get_feasibility_response` function were updated to accept the new parameters from the request and pass them to the workflow factory.

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException

import app.fastapi_config as feasibility_api_config
from app.v01.schemas import FeasibilityRequest, FeasibilityResponse
from DataFeasibility import workflow_factory

# routers are sub apps
router = APIRouter(tags=["idea"])


# core wrapper function
def get_feasibility_response(
    query: str,
    source: str,
    background_tasks: BackgroundTasks,
    llm_api_key: str,
    llm_model_name: str,
) -> FeasibilityResponse:
    """
    The function `get_response` processes a query, searches for relevant documents, generates a
    response, and asynchronously writes data to a database.

    Args:
      query (str): The `query` parameter is a string that represents the user's input or question that
    is being used to search for relevant documents and generate a response.
      config (RAGServiceConfig): RAGServiceConfig is a configuration object used for the RAG
    (Retrieval-Augmented Generation) service. It contains settings and parameters related to the
    retrieval and generation processes.
      background_tasks (BackgroundTasks): The `background_tasks` parameter in the `get_response`
    function is an object that allows you to schedule background tasks to be executed asynchronously. In
    this specific code snippet, the `background_tasks` object is used to add a task to write data to a
    database without waiting for it to complete before returning

    Returns:
      str: FeasibilityResponse object containing model response with key "content"
    """
    try:
        # Create the workflow object based on the database source
        workflow = workflow_factory.object_factory.create(
            source,
            query=query,
            llm_api_key=llm_api_key,
            llm_model_name=llm_model_name,
        )
        # Assemble and process the prompt, retrieve and generate the response
        generated_response = workflow.process()
        response = FeasibilityResponse(content=generated_response.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return response


@router.post("/idea/v01/", **feasibility_api_config.IDEA_META)
async def evaluate_idea(
    request: FeasibilityRequest, background_tasks: BackgroundTasks
) -> FeasibilityResponse:
    """
    This API endpoint evaluates the feasibility of an idea based on provided data source and query, and returns a response with the evaluation result.
    """
    return get_feasibility_response(
        request.query,
        request.source,
        background_tasks,
        request.llm_api_key,
        request.llm_model_name,
    )
```

### 3. `DataFeasibility/workflows.py`

The `DataFeasibility` workflow now dynamically configures the `ChatOpenAI` model. The `llm_api_key` and `llm_model_name` are now required parameters.

```python
import traceback
from aiweb_common.generate.AugmentedResponse import RAGResponseHandler
from aiweb_common.generate.PromptyHandler import PromptyHandler
from aiweb_common.WorkflowHandler import WorkflowHandler

from DataFeasibilityConfig import app_config, config


class DataFeasibility(WorkflowHandler):
    """
    This Python class `DataFeasibility` is designed to process data feasibility by searching documents
    based on prompts and generating a response using RAGResponseHandler.
    """

    def __init__(
        self,
        query,
        prompty_path,
        table_name,
        vectorstore_config,
        llm_api_key: str,
        llm_model_name: str,
    ):
        """
        The function initializes attributes for a query system with prompts, table name, and vector store
        configuration.

        Args:
          query: The `query` parameter is typically a string that represents a query or a question that
        needs to be processed or executed by the system. It could be a SQL query, a search query, or any
        other type of query depending on the context of your application.
          system_prompt: The `system_prompt` parameter seems to be a prompt or message used by the system.
        It is being assigned to the `self.system_prompt` attribute in the `__init__` method of a class.
          table_name: The `table_name` parameter in the `__init__` method is used to store the name of a
        table in a database or any other data storage system. It seems like this parameter is being
        initialized with the value passed to the constructor when an instance of the class is created.
          vectorstore_config: The `vectorstore_config` parameter contains configuration settings
        related to a vector store, which is a data structure used for storing and manipulating vectors in a
        machine learning or natural language processing context. This configuration may include settings
        such as the type of vector representation to use, dimensionality of the vectors, normalization
        """
        super().__init__()
        self.prompty_path = prompty_path
        self.table_name = table_name
        self.query = query
        self.vectorstore_config = vectorstore_config
        self.llm_interface = config.ChatOpenAI(
            base_url=app_config.OPENAI_COMPATIBLE_ENDPOINT,
            model=llm_model_name,
            api_key=llm_api_key,
            user=app_config.NAME,
        )
        self.prompty = PromptyHandler()

    def _search_documents(self, augmented_response, prompt):
        """
        The `_search_documents` function retrieves documents based on a given prompt from an augmented
        response.

        Args:
          augmented_response: The `augmented_response` parameter is to be an object that has
        the method `retrieve_data` which takes a `prompt` as an argument and returns some documents. In the
        `_search_documents` method, this method is called with the `prompt` parameter to retrieve documents.
          prompt: The `_search_documents` function takes two parameters:

        Returns:
          the documents retrieved based on the prompt provided.
        """
        docs = augmented_response.aug_service.retrieve_data(prompt)
        return docs

    def _assemble_input(self):
        augmented_response = RAGResponseHandler(
            self.llm_interface, config.EMBEDDINGS, self.vectorstore_config
        )
        docs = self._search_documents(augmented_response, self.query)
        input_data = {"question": self.query, "context": docs}
        return input_data

    def process(self):
        chain = self.prompty._load_prompty(self.prompty_path, self.llm_interface)

        try:
            input_data = self._assemble_input()
            result, result_meta = self.prompty.generate_response(chain, input_data)
            if result is None:
                raise ValueError("Chain returned None for the input")
            self._update_total_cost(result_meta)
            return result
        except Exception as e:
            print(f"Exception: {e}")
            traceback.print_exc()
            return None


class MPOG(DataFeasibility):
    def __init__(self, query, llm_api_key, llm_model_name):
        """
        The function initializes a class with specific parameters for a query.

        Args:
          query: The `query` parameter is typically a string or object that represents a query to be
        executed in a database or data store. It is used to retrieve specific information or data based on
        certain criteria. In the context of the `__init__` method you provided, the `query` parameter is
        being
        """
        super().__init__(
            query,
            config.MPOG_PROMPTY,
            app_config.MPOG_TABLE_NAME,
            config.MPOG_VECTORSTORE,
            llm_api_key,
            llm_model_name,
        )


class Sickbay(DataFeasibility):
    def __init__(self, query, llm_api_key, llm_model_name):
        """
        The function initializes a class with specific parameters related to a sickbay helper system.

        Args:
          query: The `query` parameter is typically a string or object that represents a query or request
        being made to a system or database. It is used to retrieve specific information or perform actions
        based on the query provided. In the context of the `__init__` method you shared, the `query`
        parameter
        """
        super().__init__(
            query,
            config.SICKBAY_PROMPTY,
            app_config.SICKBAY_TABLE_NAME,
            config.SICKBAY_VECTORSTORE,
            llm_api_key,
            llm_model_name,
        )


class Compurecord(DataFeasibility):
    def __init__(self, query, llm_api_key, llm_model_name):
        """
        The function initializes an object with specific parameters for a query.

        Args:
          query: The `query` parameter in the `__init__` method is typically used to pass a query string or
        object to the constructor of a class. It seems like in this case, the `query` parameter is being
        passed to the superclass constructor along with other parameters. The specific purpose and usage of
        """
        super().__init__(
            query,
            config.COMPURECORD_PROMPTY,
            app_config.COMPURECORD_TABLE_NAME,
            config.COMPURECORD_VECTORSTORE,
            llm_api_key,
            llm_model_name,
        )
```

### 4. `DataFeasibility/workflow_factory.py`

The object factory was updated to use `lambda` functions to pass the new keyword arguments to the workflow constructors.

```python
from enum import Enum

from aiweb_common.ObjectFactory import ObjectFactory

from DataFeasibility.workflows import MPOG, Compurecord, Sickbay


# The class `DatabaseName` defines an enumeration with three database name options: `mpog`, `sickbay`,
# and `compurecord`.
class DatabaseName(str, Enum):
    mpog = "mpog"
    sickbay = "sickbay"
    compurecord = "compurecord"


object_factory = ObjectFactory()
object_factory.register_builder(
    DatabaseName.mpog,
    lambda **kwargs: MPOG(
        query=kwargs.get("query"),
        llm_api_key=kwargs.get("llm_api_key"),
        llm_model_name=kwargs.get("llm_model_name"),
    ),
)
object_factory.register_builder(
    DatabaseName.sickbay,
    lambda **kwargs: Sickbay(
        query=kwargs.get("query"),
        llm_api_key=kwargs.get("llm_api_key"),
        llm_model_name=kwargs.get("llm_model_name"),
    ),
)
object_factory.register_builder(
    DatabaseName.compurecord,
    lambda **kwargs: Compurecord(
        query=kwargs.get("query"),
        llm_api_key=kwargs.get("llm_api_key"),
        llm_model_name=kwargs.get("llm_model_name"),
    ),
)
```

### 5. `DataFeasibilityConfig/config.py`

The static `CHAT` object was removed, as the `ChatOpenAI` model is now instantiated dynamically in the `DataFeasibility` workflow.

### 6. `tests/fastapi_tests/test_api.py`

The test suite was updated to reflect the new mandatory fields. All test cases in `test_api_responses` now include only the required fields in the payload, and the API key is sent in the Authorization header. A test case was added to verify that requests missing required fields return a 422 validation error. A test, `test_api_invalid_key`, ensures that the API handles invalid API keys gracefully by returning a 500 status code.

## Testing

The API now requires each test request to include the OpenAI-compatible endpoint and model in the JSON body and the API key in the `Authorization` header. There is no fallback to configuration or secrets in tests — tests must supply `openai_compatible_endpoint`, `openai_compatible_model`, and an `Authorization: Bearer <api_key>` header on every request. See the checklist at the end for a compact conversion guide.

Required request shape (example)
```json
{
  "query": "How many patients match X?",
  "source": "mpog",
  "openai_compatible_endpoint": "https://example-openai-compatible-host/",
  "openai_compatible_model": "gpt-4-azure"
}
```

Required header example
```
Authorization: Bearer test-api-key-123
```

What to mock in tests and why
- [`config.ChatOpenAI`](DataFeasibility/workflows.py:186) (or whichever class is dynamically instantiated to call the LLM): Mock to avoid real network calls and to simulate LLM exceptions (e.g., unauthorized) for error paths.
- [`aiweb_common.generate.PromptyHandler`](DataFeasibility/workflows.py:192): Mock `PromptyHandler.generate_response` (and `_load_prompty` if needed) because prompt handling returns controlled results used by the workflow.
- [`aiweb_common.generate.AugmentedResponse.RAGResponseHandler`](DataFeasibility/workflows.py:212): Mock its `aug_service.retrieve_data` to return deterministic document context for the prompt assembly.
- `tiktoken.encoding_for_model` (if exercised by your code paths): Mock to avoid requiring the tiktoken package or specific model encodings during tests.

Why each must be mocked
- Chat/LLM class: prevents network/credential use and lets you simulate success, latency, and failures.
- PromptyHandler: it returns the actual "result" object that the API returns; mocking lets tests control the content and metadata shape.
- RAGResponseHandler/aug_service: avoids vectorstore and embedding interactions.
- tiktoken.encoding_for_model: avoids runtime dependency on tokenizers and model-specific encodings.

Shaping mocks (exact guidance)
- PromptyHandler.generate_response should return a tuple: (result_object, result_meta)
  - result_object must have a .content attribute (string).
  - result_meta must be an object/dict with any attributes your code reads (e.g., total_cost).
- Example minimal construction using unittest.mock.Mock:

```python
from unittest.mock import Mock

result_object = Mock()
result_object.content = "This is a mocked LLM response"

result_meta = Mock()
result_meta.total_cost = 0.001
# generate_response returns (result_object, result_meta)
mock_generate_response.return_value = (result_object, result_meta)
```

Concise pytest + FastAPI TestClient example (copy-pasteable)
- This example shows building the JSON body and headers, patching `PromptyHandler.generate_response`, and asserting a successful response.

```python
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.server import app  # or the path to your FastAPI app

client = TestClient(app)

def test_idea_endpoint_happy_path():
    payload = {
        "query": "test query",
        "source": "mpog",
        "openai_compatible_endpoint": "https://example-openai-compatible-host/",
        "openai_compatible_model": "gpt-4-azure"
    }
    headers = {"Authorization": "Bearer test-api-key-123"}

    # Patch PromptyHandler.generate_response where it's imported by the code under test.
    # IMPORTANT: patch the import path the code uses; see "patching import paths" below.
    with patch("aiweb_common.generate.PromptyHandler.PromptyHandler.generate_response") as mock_generate:
        # Construct mock return values
        result_object = Mock()
        result_object.content = "mocked content"
        result_meta = Mock()
        result_meta.total_cost = 0.0
        mock_generate.return_value = (result_object, result_meta)

        response = client.post("/idea/v01/", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "mocked content"
```

Simulating error cases
- Missing required fields → expect 422:
```python
def test_missing_fields_returns_422():
    payload = {"query": "a", "source": "mpog"}  # missing endpoint/model
    headers = {"Authorization": "Bearer test-api-key-123"}
    resp = client.post("/idea/v01/", json=payload, headers=headers)
    assert resp.status_code == 422
```

- Invalid/unauthorized API key → simulate by making the mocked Chat class raise an exception:
```python
from unittest.mock import patch

def test_invalid_api_key_results_in_500():
    payload = {
        "query": "q",
        "source": "mpog",
        "openai_compatible_endpoint": "https://example/",
        "openai_compatible_model": "gpt-4-azure"
    }
    headers = {"Authorization": "Bearer bad-key"}
    # Patch the ChatOpenAI (or equivalent) constructor/call to raise
    with patch("DataFeasibility.workflows.config.ChatOpenAI") as mock_chat:
        mock_chat.side_effect = Exception("unauthorized")
        resp = client.post("/idea/v01/", json=payload, headers=headers)
        assert resp.status_code == 500
```

Patching import paths — common pitfalls and explicit examples
- Always patch the name as it is imported by the module under test, not necessarily where it is defined.
  - If `DataFeasibility.workflows` does `from aiweb_common.generate.PromptyHandler import PromptyHandler`, you must patch:
    - "DataFeasibility.workflows.PromptyHandler.generate_response" or patch the class: "DataFeasibility.workflows.PromptyHandler"
  - If code constructs Chat via `config.ChatOpenAI` inside `DataFeasibility.workflows`, patch:
    - "DataFeasibility.workflows.config.ChatOpenAI"
  - For `RAGResponseHandler` used in `DataFeasibility.workflows`, patch:
    - "DataFeasibility.workflows.RAGResponseHandler"
  - For `tiktoken.encoding_for_model` calls, patch the import path used by the tested module, e.g.:
    - "DataFeasibility.some_module.tiktoken.encoding_for_model"

Common gotchas and how to fix them
- AttributeError from None: ensure your mocked method returns a non-None object/value (e.g., return (Mock(), Mock())) not None.
- Wrong mock return shape: match the exact shape the code expects (tuple of (result, result_meta), result has .content). Inspect the code under test to confirm attributes read.
- Patching wrong import path: if the patch appears to have no effect, switch to patching the symbol as referenced by the module under test (see examples above).
- tiktoken-related errors: mock `encoding_for_model` to return a simple object with encode/decode stubs if your code calls them.

Checklist: converting an existing test
- [ ] Add `openai_compatible_endpoint` and `openai_compatible_model` to the JSON request body.
- [ ] Add `Authorization: Bearer <api_key>` header to the request.
- [ ] Patch/mocks:
  - [ ] Patch the Chat/LLM class used by the workflow (e.g., `DataFeasibility.workflows.config.ChatOpenAI`).
  - [ ] Patch `PromptyHandler.generate_response` to return `(result_object, result_meta)` where `result_object.content` is a string.
  - [ ] Patch `RAGResponseHandler` or its `aug_service.retrieve_data` to return deterministic docs.
  - [ ] Patch `tiktoken.encoding_for_model` if referenced.
- [ ] Add assertions for success and error codes (200, 422, 500 as appropriate).
- [ ] Run tests and fix any AttributeError/wrong-shape issues by adjusting mock shapes or patch targets.

Reference examples in this document (files you may edit in tests):
- [`tests/fastapi_tests/v01/test_process_endpoint.py`](tests/fastapi_tests/v01/test_process_endpoint.py:1)
- [`DataFeasibility/workflows.py`](DataFeasibility/workflows.py:1)
- [`app/v01/schemas.py`](app/v01/schemas.py:1)

This Testing section provides concrete, copy‑pasteable examples and explicit patch targets so contributors can reproduce the changes and write new tests that follow the client-supplied LLM credentials paradigm.
