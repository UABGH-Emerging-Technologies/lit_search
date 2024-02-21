# config.py
import logging
import sys
from pathlib import Path

import mlflow
from rich.logging import RichHandler

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import AzureChatOpenAI

# Development Directories
BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = Path(BASE_DIR, "config")
LOGS_DIR = Path(BASE_DIR, "logs")

# Data Directories
DATA_DIR = Path("/data/DATASCI")
RAW_DATA = Path(DATA_DIR, "raw")
INTERMEDIATE_DIR = Path(DATA_DIR, "intermediate")
RESULTS_DIR = Path(DATA_DIR, "results")

# DATABASE Interface definitions
DB_SERVER = manage_sensitive("db_server")
DB_NAME = manage_sensitive("db_name")
DB_USER = manage_sensitive("db_user")
DB_PASSWORD = manage_sensitive("db_password")
OPENAI_API_KEY = manage_sensitive("openai_api_key")

# openai
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

#Assets
ASSETS_DIR = Path(BASE_DIR, "assets")

ScopingReview_VECTORSTORE 

# LLM specific
EMBEDDINGS = OpenAIEmbeddings(
            deployment="AdaEmbedding2",
            model="text-embedding-ada-002",
            openai_api_base="https://nlp-openai-svc.openai.azure.com",
            openai_api_type="azure",
            chunk_size=1
        )

CHAT = AzureChatOpenAI(
    openai_api_base="https://nlp-openai-svc.openai.azure.com",
    openai_api_version="2023-03-15-preview",
    deployment_name="ChatGPT35Turbo",
    openai_api_type = "azure",
    temperature=0
)

# MLFlow model registry
mlflow.set_tracking_uri("http://localhost:5000")

# Logger
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "minimal": {"format": "%(message)s"},
        "detailed": {
            "format": "%(levelname)s %(asctime)s [%(name)s:%(filename)s:%(funcName)s:%(lineno)d]\n%(message)s\n"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "minimal",
            "level": logging.DEBUG,
        },
        "info": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGS_DIR, "info.log"),
            "maxBytes": 10485760,  # 1 MB
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.INFO,
            "mode": "a+", 
        },
        "error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGS_DIR, "error.log"),
            "maxBytes": 10485760,  # 1 MB
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.ERROR,
            "mode": "a+", 
        },
    },
    "root": {
        "handlers": ["console", "info", "error"],
        "level": logging.INFO,
        "propagate": True,
    },
}
logging.config.dictConfig(logging_config)
logger = logging.getLogger()
logger.handlers[0] = RichHandler(markup=True)
