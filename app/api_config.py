DOCX_EXPECTED_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

LIT_API_META = {
    "summary": "Get help with a literature search.",
    "description": "Takes in qeustions, xlsx, or docx files and returns the output of a literature search step.",
    "response_description": "XLSX or DOCX file.",
    "responses": {
        200: {
            "description": "A DOCX or XLSX file.",
        },
        415: {"description": "Unsupported file type."},
    },
}