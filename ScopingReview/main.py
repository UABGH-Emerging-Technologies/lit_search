import warnings
import mlflow
import typer
import copy
from ScopingReview import prompts

from ScopingReview_config import config
from ScopingReview_config.config import logger

from ScopingReview.data import ingest_scoping_review_csv
from ScopingReview.generate import search_scoping_review_vectorstore, get_scoping_review_response

# Initialize Typer CLI app
app = typer.Typer()
warnings.filterwarnings("ignore")


@app.command()
def ingest_scoping_review(
    experiment_name: str = 'index_scoping_review',
    run_name: str = "faiss",
    test_run: bool = True,
):
  raise NotImplementedError
        
@app.command()
def generate_scoping_review(
    query: str,
    experiment_name: str = 'interrogate_scoping_review',
    run_name: str = "qa",
    mlflow_logging: bool = True,
):
  raise NotImplementedError
            

if __name__ == "__main__":
    app()  # pragma: no cover, live app
