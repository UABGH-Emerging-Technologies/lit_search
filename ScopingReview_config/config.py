# config.py
import sys
from pathlib import Path

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_openai.chat_models.base import ChatOpenAI

import ScopingReview_config.app_config as lit_app_config

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
EXCEL_MIME = "application/vnd.ms-excel"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# BUTTON LABELS
EXCEL_DOWNLOAD_LABEL = "Download Excel File"
DOCX_DOWNLOAD_LABEL = "Download Word Document"
BOTH_FILES = "Download Files"
BIB_DOWNLOAD_LABEL = "Download .bib File"

# LOOP Counting
MAX_TRIES = 6

# Sub Classificaiton threshold
SUBCLASS_THRESHOLD = 40

# Newsletter
NEWSLETTER_QUESTION = "Developments in {category} anesthesia that may impact clinical practice"
NEWSLETTER_CATEGORIES = ["pain", "perioperative medicine",  "cardiac", "OB", "regional", "general", "critical care"]
NEWSLETTER_QUERIES = {
    "cardiac": "cardiac anesthesia OR cardiac anaesthesia OR cardiac anesthesiology OR heart anesthesia OR cardiothoracic anesthesia OR cardiothoracic anesthesiology",
    "OB": "obstetric anesthesia OR obstetric anaesthesia OR maternal anesthesia OR perinatal anesthesia",
    "regional": "regional anesthesia OR regional anaesthesia OR nerve block OR spinal anesthesia OR epidural anesthesia",
    "general": '(general anesthesia OR general anaesthesia) AND (("Anesthesiology"[ta]) OR ("Anesthesia and Analgesia"[ta]) OR ("British Journal of Anaesthesia"[ta]) OR ("Journal of Clinical Anesthesia"[ta]) OR ("JAMA"[ta]) OR ("Journal of the American Medical Association"[ta]))',
    "critical care": "critical care anesthesia OR critical care anaesthesia OR ICU anesthesia OR intensive care anesthesia",
    "perioperative medicine": '(perioperative[tiab] OR preoperative[tiab] OR postoperative[tiab]) AND (anesthesia[tiab] OR anesthesiology[tiab] OR surgery[tiab] OR surgical[tiab] OR "noncardiac surgery"[tiab]) AND (myocardial injury[tiab] OR MINS[tiab] OR stroke[tiab] OR hypoxia[tiab] OR frailty[tiab] OR mortality[tiab] OR "postoperative complications"[tiab] OR readmission[tiab] OR "cognitive dysfunction"[tiab] OR anemia[tiab] OR transfusion[tiab] OR "diabetic ketoacidosis"[tiab] OR "aspiration pneumonia"[tiab] OR "Duke Activity Status Index"[tiab] OR DASI[tiab] OR "frailty index"[tiab] OR "ASA classification"[tiab] OR eGFR[tiab] OR NT-proBNP[tiab] OR Hs-Trop[tiab] OR hs-TnT[tiab] OR TTE[tiab] OR "risk calculator"[tiab] OR "machine learning"[tiab] OR MACE[tiab] OR MICA[tiab] OR AUB-HAS2[tiab] OR "SGLT2 inhibitor*"[tiab] OR "tranexamic acid"[tiab] OR TXA[tiab] OR lidocaine[tiab] OR "GLP-1 receptor agonist*"[tiab] OR "oral iron"[tiab] OR "iron supplementation"[tiab] OR "direct oral anticoagulant*"[tiab] OR DOAC*[tiab] OR cannabinoids[tiab] OR cannabis[tiab] OR "spinal anesthesia"[tiab] OR "implantable device*"[tiab] OR DBS[tiab] OR SCS[tiab] OR VNS[tiab] OR neurostimulation[tiab] OR HFNC[tiab] OR "Enhanced Recovery After Surgery"[tiab] OR ERAS[tiab] OR "patient blood management"[tiab] OR PBM[tiab] OR "goal-directed therapy"[tiab] OR "perioperative optimization"[tiab] OR checklist*[tiab] OR guideline*[tiab] OR elderly[tiab] OR "older adult*"[tiab] OR cancer[tiab] OR diabetes[tiab] OR "chronic kidney disease"[tiab] OR CKD[tiab] OR "heart disease"[tiab] OR obesity[tiab] OR (noncardiac[tiab] AND surgery[tiab] AND complications[tiab]) OR (preoperative[tiab] AND cardiac[tiab] AND biomarker*[tiab]) OR "anesthesia in elderly patients"[tiab] OR "ERAS protocol implementation"[tiab] OR "perioperative management"[tiab] OR "postoperative outcomes"[tiab]) AND ("Perioperative Care"[Mesh] OR "Preoperative Care"[Mesh] OR "Anesthesia"[Mesh] OR Journal of Perioperative Medicine[ta] OR "Journal of Clinical Anesthesia"[ta] OR "Current Opinion in Anaesthesiology"[ta] OR "Current Anesthesiology Reports"[ta] OR "British Journal of Anaesthesia"[ta] OR "Anesthesiology Clinics"[ta] OR "International Anesthesiology Clinics"[ta] OR Anesth Analg[ta] OR "JAMA Surgery"[ta] OR "NEJM Evid"[ta] OR Anesthesiology[ta])',
    "pain": '(("Pain"[ta]) OR ("Pain Med"[ta]) OR ("J Pain"[ta]))'
}


# LLM
CHAT = ChatOpenAI(
    base_url=lit_app_config.OPENAI_COMPATIBLE_ENDPOINT,
    model=lit_app_config.CHAT_MODEL_NAME,
    api_key=lit_app_config.OPENAI_COMPATIBLE_KEY,
    user=lit_app_config.NAME,
)

ChatOpenAI(
    base_url=lit_app_config.OPENAI_COMPATIBLE_ENDPOINT,
    model=lit_app_config.SUMMARIZE_MODEL_NAME,
    api_key=lit_app_config.OPENAI_COMPATIBLE_KEY,
    user=lit_app_config.NAME,
)

# pubmed settings
MIN_ARTICLES = 10
MAX_ARTICLES_SR = 200
MAX_ARTICLES_LR = 50

# remove this later
CHAT35 = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2024-02-01",
    azure_deployment="ChatGPT16k",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-35-turbo-16",
    api_key=lit_app_config.GPT4_KEY,
)
