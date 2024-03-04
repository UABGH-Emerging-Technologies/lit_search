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
    
def format_authors(author_list):
    """
    The function `format_authors` takes a list of dictionaries representing authors and returns a
    formatted string of their last names followed by initials, following APA rules.
    
    Args:
      author_list: A list of dictionaries, where each dictionary represents an author and contains the
                    keys "LastName" and "Initials".
    
    Returns:
      a formatted string of authors' names in the format "Last Name, Initials," following APA rules.
    """
    formatted_authors = []
    num_authors = len(author_list)
    
    if num_authors <= 20:
        # Normal case, just list all authors
        for author in author_list:
            last_name = author.get("LastName", "")
            initials = author.get("Initials", "")
            formatted_authors.append(f"{last_name}, {initials}.")
        return ", ".join(formatted_authors)
    else:
        # APA rule for > 20 authors: first 19, ellipsis, last author
        for author in author_list[:19]:
            last_name = author.get("LastName", "")
            initials = author.get("Initials", "")
            formatted_authors.append(f"{last_name}, {initials}.")
        
        last_author = author_list[-1]
        last_author_name = last_author.get("LastName", "")
        last_author_initials = last_author.get("Initials", "")
        
        formatted_authors.append("…")
        formatted_authors.append(f"{last_author_name}, {last_author_initials}.")
        
        return ", ".join(formatted_authors)
