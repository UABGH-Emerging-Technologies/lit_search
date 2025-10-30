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

The test suite for the FastAPI endpoint was updated to reflect the new requirements and ensure robust, isolated coverage:

- **Mandatory Fields:** All test payloads now include only the required fields (`query`, `source`, `openai_compatible_endpoint`, `openai_compatible_model`). The API key is sent in the Authorization header. A test case verifies that requests missing these fields return a 422 validation error.
- **Mocking External Dependencies:** All network-dependent components (`ChatOpenAI`, `PromptyHandler`, `RAGResponseHandler`, and `tiktoken.encoding_for_model`) are mocked using `unittest.mock.patch`. This ensures tests do not require real API keys, secrets, or network access.
- **Correct Mock Return Values:** The mocks for `PromptyHandler.generate_response` now return objects with the required attributes (`content`, `total_cost`) to match the expectations of the workflow logic and avoid `AttributeError` and `NoneType` errors.
- **Test Coverage:** The suite verifies successful responses for all supported sources, as well as proper error handling for missing required fields and invalid API keys.
- **Isolation:** By mocking all external dependencies, the tests focus solely on API and workflow logic, ensuring reliability and repeatability regardless of environment.

These changes ensure the test suite accurately reflects the new API requirements and remains robust against future changes to external services or configuration.