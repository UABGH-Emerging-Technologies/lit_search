"""Application metadata and external API key management."""

from ScopingReview_config.secrets_util import require_secret

NAME = "lit"

# LLM specific
# libkey
LIBKEY_API_KEY = require_secret("libkey_api_key")

# NCBI
NCBI_API_KEY = require_secret("ncbi_api_key")

UAB_LIBKEY_ID = "731"
