from aiweb_common.file_operations.file_handling import create_base64_file_validator

import app.fastapi_config as lit_api_config

validate_docx_bytes = create_base64_file_validator(
    lit_api_config.DOCX_EXPECTED_TYPE
)


validate_xlsx_bytes = create_base64_file_validator(
    lit_api_config.XLSX_EXPECTED_TYPE
)