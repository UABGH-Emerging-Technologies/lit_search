"""Application metadata and external API key management."""

from aiweb_common.WorkflowHandler import manage_sensitive

NAME = "lit"

# LLM specific
# libkey
LIBKEY_API_KEY = manage_sensitive("libkey_api_key")

# NCBI
NCBI_API_KEY = manage_sensitive("ncbi_api_key")

UAB_LIBKEY_ID = "731"
