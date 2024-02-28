from langchain.vectorstores import FAISS
from langchain.document_loaders.csv_loader import CSVLoader
import ScopingReview_config.config as helper_config


def ingest_scoping_review_csv(

    ):
    """
    This function ingests a CSV file, converts it into a document format, creates a FAISS index using
    embeddings, and saves the index to a local file.
    
    Args:
      path: The path to the MPOG CSV file that contains the data to be ingested.
      embeddings: The embeddings parameter is a path to a file containing pre-trained word embeddings.
    These embeddings are used to convert the text data in the CSV file into numerical vectors that can
    be used for similarity search.
      out: The `out` parameter is the output path where the vector store generated from the MPOG CSV
    file will be saved.
    """
    # scoping_review_csv_loader = CSVLoader(file_path=path)
    # scoping_review_documents = scoping_review_csv_loader.load()
    # scoping_review_db = FAISS.from_documents(scoping_review_documents, embeddings)
    # scoping_review_db.save_local(out)
