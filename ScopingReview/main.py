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
    """
    The `ingest` function preprocesses data and logs the csv ingestion steps using MLflow if `test_run`
    is False.
    
    Args:
      experiment_name (str): A string representing the name of the experiment to be logged in MLflow.
    Defaults to index_scoping_review
      run_name (str): The name of the MLflow run that will be created to log the preprocessing
    information. Defaults to faiss
      test_run (bool): The `test_run` parameter is a boolean flag that determines whether the function
    should run in test mode or not. If `test_run` is set to `True`, the function will run in test mode
    and skip certain steps that are not necessary for testing. If `test_run` is set to. Defaults to True
    """
    ingest_scoping_review_csv(path=config.ScopingReview_CSV, embeddings=config.EMBEDDINGS, out=config.ScopingReview_VECTORSTORE)

    if not test_run:
        #Log preproccesing
        logger.info("✅ sucessfully preprocessed data")
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name):
            embeddings_args = copy.copy(config.EMBEDDINGS.__dict__)
            del embeddings_args['openai_api_key']
            mlflow.log_params(embeddings_args)
            mlflow.log_param("output_filepath", config.ScopingReview_VECTORSTORE)
            mlflow.log_param("input_filepath", config.scoping_review_CSV)
   
        
@app.command()
def generate_scoping_review(
    query: str,
    experiment_name: str = 'interrogate_scoping_review',
    run_name: str = "qa",
    mlflow_logging: bool = True,
):
    """
    The function generates a response to a user query and logs the results using MLflow if specified.
    
    Args:
      query (str): The user's query or input text that will be used to generate a response.
      experiment_name (str): The name of the experiment to be logged in MLflow. An experiment is a
    container for runs, which are executions of code against a specific version of code and data.
    Defaults to interrogate_scoping_review
      run_name (str): The name of the run for logging purposes. It is set to "qa" by default. Defaults
    to qa
      mlflow_logging (bool): mlflow_logging is a boolean parameter that determines whether to log the
    results of the function using MLflow. If set to True, the function will log the experiment name, run
    name, embeddings, model, user query, and model response using MLflow. If set to False, the function
    will not. Defaults to True
    """
    docs = search_scoping_review_vectorstore(query,
                                   embeddings=config.EMBEDDINGS,
                                   store=config.ScopingReview_VECTORSTORE)
    result = get_scoping_reviews_response(query,
                                docs,
                                chat=config.CHAT,
                                chat_prompt=prompts.chat_prompt)
    #Log 
    if mlflow_logging:
        logger.info("✅ sucessfully preprocessed data")
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name):
            embeddings_args = copy.copy(config.EMBEDDINGS.__dict__)
            del embeddings_args['openai_api_key']
            model_args = copy.copy(config.CHAT.__dict__)
            del model_args['openai_api_key']
            mlflow.log_params(embeddings_args)
            mlflow.log_params(model_args)
            mlflow.log_param("user_query", query)
            mlflow.log_param("model_response", result.content)
    return result.content
            

if __name__ == "__main__":
    app()  # pragma: no cover, live app
