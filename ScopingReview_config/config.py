"""Application configuration: file paths, thresholds, PubMed settings, and newsletter queries."""

import re
import sys
from pathlib import Path
from re import Pattern

import ScopingReview_config.app_config as lit_app_config

# Responses API detection for GPT-5 series models
_GPT5_PATTERN: Pattern[str] = re.compile(r"^gpt-?5", re.IGNORECASE)


def _is_responses_api_model(model_name: str) -> bool:
    """Return True if the model should use the Responses API."""
    return bool(_GPT5_PATTERN.match(model_name))


# Reasoning effort for GPT-5 series models ("low", "medium", "high")
REASONING_EFFORT = "low"

# Development Directories
BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = Path(BASE_DIR, "config")
LOGS_DIR = Path(BASE_DIR, "logs")
DEV_EMAIL = "rmelvin@uabmc.edu"


# Assets
ASSETS_DIR = Path(BASE_DIR, "assets")

# ScopingReview_outname
SR_STEP1_FILENAME = "InitialSearch.xlsx"
SR_STEP2_FILENAME = "IteratedSearch.xlsx"
SR_STEP3_FILENAME = "CategorizedArticles.xlsx"
SR_STEP4_DOCX_FILENAME = "SummarizedArticles.docx"
SR_STEP4_EXCEL_FILENAME = "SubcategorizedArticles.xlsx"
SR_STEP5_FILENAME = "ScopingReview_FirstDraft.docx"
SR_STEP6_FILENAME = "ScopingReview_Bibliography.bib"

# MIMES
EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# BUTTON LABELS
EXCEL_DOWNLOAD_LABEL = "Download Excel File"
DOCX_DOWNLOAD_LABEL = "Download Word Document"
BOTH_FILES = "Download Files"
BIB_DOWNLOAD_LABEL = "Download .bib File"

# LOOP Counting
MAX_TRIES = 6

# Sub Classificaiton threshold
SUBCLASS_THRESHOLD = 60

# Newsletter
NEWSLETTER_QUESTION = "Developments in {category} anesthesia that may impact clinical practice"
NEWSLETTER_CATEGORIES = ["cardiac", "OB", "regional", "general", "critical care"]
NEWSLETTER_QUERIES = {
    "cardiac": "cardiac anesthesia OR cardiac anaesthesia OR cardiac anesthesiology OR heart anesthesia OR cardiothoracic anesthesia OR cardiothoracic anesthesiology",
    "OB": "obstetric anesthesia OR obstetric anaesthesia OR maternal anesthesia OR perinatal anesthesia",
    "regional": "regional anesthesia OR regional anaesthesia OR nerve block OR spinal anesthesia OR epidural anesthesia",
    "general": "general anesthesia OR general anaesthesia",
    "critical care": "critical care anesthesia OR critical care anaesthesia OR ICU anesthesia OR intensive care anesthesia",
}


# pubmed settings
MIN_ARTICLES = 10
MAX_ARTICLES_SR = 200
MAX_ARTICLES_LR = 50
