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


# LLM specific
EMBEDDINGS = AzureOpenAIEmbeddings(
    azure_deployment="NewAda2",
    model="text-embedding-ada-002",
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_type="azure",
    chunk_size=1,
    openai_api_key = lit_app_config.GPT4_KEY
)

CHAT = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2023-06-01-preview",
    azure_deployment="ChatGPT4",
    openai_api_type="azure",
    temperature=0.8,
    model_name="gpt-4",
    openai_api_key=lit_app_config.GPT4_KEY
)

SUMMARIZE_CHAT = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2023-06-01-preview",
    azure_deployment="ChatGPT432k",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-4-32k",
    openai_api_key=lit_app_config.GPT4_KEY
)

# pubmed settings
MIN_ARTICLES = 10
MAX_ARTICLES_SR = 200
MAX_ARTICLES_LR = 50

# remove this later
FASTER_CHAT = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2024-02-15-preview",
    azure_deployment="ChatGPT16k",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-35-turbo-16",
    openai_api_key=lit_app_config.GPT4_KEY
)