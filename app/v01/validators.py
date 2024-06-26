from llm_utils import api_utils

import app.fastapi_config as lit_api_config

validate_docx_bytes = api_utils.create_base64_file_validator(
    lit_api_config.DOCX_EXPECTED_TYPE
)


validate_xlsx_bytes = api_utils.create_base64_file_validator(
    lit_api_config.XLSX_EXPECTED_TYPE
)