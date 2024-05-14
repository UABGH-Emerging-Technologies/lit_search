import ScopingReview_config.config as lit_config

DOCX_EXPECTED_TYPE = lit_config.DOCX_MIME
XLSX_EXPECTED_TYPE = lit_config.EXCEL_MIME

LIT_API_META = {
    "summary": "Get help with a literature search.",
    "description": "Takes in qeustions, xlsx, or docx files and returns the output of a literature search step.",
    "response_description": "XLSX or DOCX file.",
    "responses": {
        200: {
            "description": "A DOCX or XLSX file.",
        }
    },
}

STANDALONE_SUMMARY_META = {
    "summary": "Get an overview of literature relevant to a research question.",
    "description": "Takes question as a string and returns a DOCX file with gauranteed-real citations.",
    "response_description": "Returns a DOCX literature summary with no citation hallucination",
    "responses": {
        200: {
            "content": {DOCX_EXPECTED_TYPE: {}},
            "description": "A DOCX file.",
        }
    },
    "operation_id": "StandaloneSummary",
}

SCOPING_STEP1_META = {
    "summary": "Start a scoping review by getting an Excel file from an initial literature search",
    "description": "Takes in a scoping review research question and returns an Excel file with each row representing a published article.",
    "response_description": "Returns an XLSX file with one row per article.",
    "responses": {
        200: {
            "content": {XLSX_EXPECTED_TYPE: {}},
            "description": "An XLSX file.",
        }
    },
    "operation_id": "ScopingStep1",
}