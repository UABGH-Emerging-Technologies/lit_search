# config.py
import sys
from pathlib import Path
from langchain_openai import AzureOpenAIEmbeddings
from langchain_openai import AzureChatOpenAI

import ScopingReview_config.app_config as lit_app_config

# Development Directories
BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = Path(BASE_DIR, "config")
LOGS_DIR = Path(BASE_DIR, "logs")
DEV_EMAIL = "rmelvin@uabmc.edu"


#Assets
ASSETS_DIR = Path(BASE_DIR, "assets")

#ScopingReview_outname 
SR_STEP1_FILENAME="InitialSearch.xlsx"
SR_STEP2_FILENAME="IteratedSearch.xlsx"
SR_STEP3_FILENAME="CategorizedArticles.xlsx"
SR_STEP4_DOCX_FILENAME="SummarizedArticles.docx"
SR_STEP4_EXCEL_FILENAME="SubcategorizedArticles.xlsx"
SR_STEP5_FILENAME="ScopingReview_FirstDraft.docx"
SR_STEP6_FILENAME="ScopingReview_Bibliography.bib"

#MIMES
EXCEL_MIME = "application/vnd.ms-excel"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

#BUTTON LABELS
EXCEL_DOWNLOAD_LABEL = "Download Excel File"
DOCX_DOWNLOAD_LABEL = "Download Word Document"
BOTH_FILES = "Download Files"
BIB_DOWNLOAD_LABEL = "Download .bib File"

#LOOP Counting
MAX_TRIES = 6

#Sub Classificaiton threshold
SUBCLASS_THRESHOLD = 40

# Newsletter
NEWSLETTER_QUESTION = "Developments in {category} anesthesia that may impact clinical practice"
NEWSLETTER_CATEGORIES = ["cardiac", "OB", "regional", "general", "critical care"]
NEWSLETTER_QUERIES = {
    "cardiac": "cardiac anesthesia OR cardiac anaesthesia OR cardiac anesthesiology OR heart anesthesia OR cardiothoracic anesthesia OR cardiothoracic anesthesiology",
    "OB": "obstetric anesthesia OR obstetric anaesthesia OR maternal anesthesia OR perinatal anesthesia",
    "regional": "regional anesthesia OR regional anaesthesia OR nerve block OR spinal anesthesia OR epidural anesthesia",
    "general": "general anesthesia OR general anaesthesia",
    "critical care": "critical care anesthesia OR critical care anaesthesia OR ICU anesthesia OR intensive care anesthesia"
}


# LLM
CHAT = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2023-06-01-preview",
    azure_deployment="ChatGPT4",
    openai_api_type="azure",
    temperature=0.8,
    model_name="gpt-4",
    api_key=lit_app_config.GPT4_KEY
)

SUMMARIZE_CHAT = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2023-06-01-preview",
    azure_deployment="ChatGPT432k",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-4-32k",
    api_key=lit_app_config.GPT4_KEY
)

# pubmed settings
MIN_ARTICLES = 10
MAX_ARTICLES_SR = 200
MAX_ARTICLES_LR = 50

# remove this later
CHAT35 = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2024-02-15-preview",
    azure_deployment="ChatGPT16k",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-35-turbo-16",
    api_key=lit_app_config.GPT4_KEY
)
