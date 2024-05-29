import ScopingReview_config.config as lit_config

DOCX_EXPECTED_TYPE = lit_config.DOCX_MIME
XLSX_EXPECTED_TYPE = lit_config.EXCEL_MIME

LIT_API_META = {
    "summary": "Get help with a literature search.",
    "description": "Takes in questions, xlsx, or docx files and returns the output of a literature search step.",
    "response_description": "XLSX or DOCX file."
}

STANDALONE_SUMMARY_META = {
    "summary": "Get an overview of literature relevant to a research question.",
    "description": "Takes question as a string and returns a DOCX file with gauranteed-real citations.",
    "response_description": "Returns a DOCX literature summary with no citation hallucination",
    "responses": {
        200: {
            "content": {
                DOCX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an DOCX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the DOCX file."
        }
    },
    "operation_id": "StandaloneSummary",
}


STANDALONE_BIBLIOGRAPHY_META = {
    "summary": "Generate a bibliography importable to a citation manager.",
    "description": "Takes a file extension (starting with a '.') and corresponding DOCX or XLXS file as a byte-enocided string created by one of our tools and returns a bibtex file. All programmatic, no AI.",
    "response_description": "Returns a bibtex file.",
    "responses": {
        200: {
            "description": "a BIB file as a byte-encoded string",
        }
    },
    "operation_id": "StandaloneBibliography",
}

SCOPING_STEP1_META = {
    "summary": "Start a scoping review by getting an Excel file from an initial literature search",
    "description": "Takes in a scoping review research question and returns an Excel file with each row representing a published article.",
    "response_description": "Returns an XLSX as a byte-encoded string file with one row per article.",
    "responses": {
        200: {
            "content": {
                XLSX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an XLSX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the XLSX file."
        }
    },
    "operation_id": "ScopingStep1",
}

SCOPING_STEP2KEYWORDS_META = {
    "summary": "Iterate on a literature search for a scoping review.",
    "description": "Takes the scoping review research question and output of step1 with user annotations in the first two columns indicating article relevance and returns a suggested set of search terms.",
    "response_description": "Returns three lists of keywords for the user to revise.",
    "responses": {
        200: {
            "description": "Three lists of keywords.",
        }
    },
    "operation_id": "ScopingStep2Keywords",
}

SCOPING_STEP2EXCEL_META = {
    "summary": "Iterate on a literature search for a scoping review.",
    "description": "Takes the scoping review research question,  output of step1 with user annotations in the first two columns, and revised sets of keywords.",
    "response_description": "Returns an excel file with the refined and expanded search results.",
    "responses": {
        200: {
            "content": {
                XLSX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an XLSX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the XLSX file."
        }
    },
    "operation_id": "ScopingStep2Iteration",
}


SCOPING_STEP3_META = {
    "summary": "Categorize a finalized set of articles",
    "description": "Takes in an excel spreadsheet and list of categories; assigns categories to articles.",
    "response_description": "Returns an XLSX file with one row per article with a `category` column added.",
    "responses": {
        200: {
            "content": {
                XLSX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an XLSX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the XLSX file."
        }
    },
    "operation_id": "ScopingStep3",
}

SCOPING_STEP4_META = {
    "summary": "Get a summary of each category of articles",
    "description": "Takes in an excel spreadsheet and the research question.",
    "response_description": "Returns a DOCX file with a summary of each category.",
    "responses": {
        200: {
            "content": {
                DOCX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an DOCX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the DOCX file."
        }
    },
    "operation_id": "ScopingStep4",
}

SCOPING_STEP5_META = {
    "summary": "Get a first draft of a scoping review article.",
    "description": "Takes in a DOCX file with category summaries..",
    "response_description": "Returns a DOCX file with a first draft of the article.",
    "responses": {
        200: {
            "content": {
                DOCX_EXPECTED_TYPE: {
                    "schema": {
                        "type": "string",
                        "format": "byte"
                    }
                }
            },
            "description": "Returns an DOCX file encoded in base64. The client is responsible for decoding the base64 string to retrieve the DOCX file."
        }
    },
    "operation_id": "ScopingStep5",
}