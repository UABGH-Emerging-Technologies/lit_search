from aiweb_common.WorkflowHandler import manage_sensitive

NAME = "lit"

# Database
DB_SERVER = manage_sensitive("db_server")
DB_NAME = manage_sensitive("db_name")
DB_USER = manage_sensitive("db_user")
DB_PASSWORD = manage_sensitive("db_password")

# LLM specific
OPENAI_API_KEY = manage_sensitive("openai_api_key")
GPT4_KEY = manage_sensitive("gpt4_api_key")

# libkey
LIBKEY_API_KEY = manage_sensitive("libkey_api_key")

# NCBI
NCBI_API_KEY = manage_sensitive("ncbi_api_key")

UAB_LIBKEY_ID = "731"
