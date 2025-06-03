import os

from llm_utils.sensitive import manage_sensitive

# Database
DB_SERVER = manage_sensitive("db_server")
DB_NAME = manage_sensitive("db_name")
DB_USER = manage_sensitive("db_user")
DB_PASSWORD = manage_sensitive("db_password")

# LLM specific
NAME = "data_feasibility"
# LLM setup
OPENAI_COMPATIBLE_ENDPOINT = (
    "https://proxy-ai-anes-uabmc-awefchfueccrddhf.eastus2-01.azurewebsites.net/v1"
)
OPENAI_COMPATIBLE_KEY = manage_sensitive("azure_proxy_key")
CHAT_MODEL_NAME = "o3"
SUMMARIZE_MODEL_NAME = "gpt-4.1-mini"
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
OPENAI_API_KEY = manage_sensitive("openai_api_key")
GPT4_KEY = manage_sensitive("gpt4_api_key")

# libkey
LIBKEY_API_KEY = manage_sensitive("libkey_api_key")

# NCBI
NCBI_API_KEY = manage_sensitive("ncbi_api_key")

UAB_LIBKEY_ID = "731"
