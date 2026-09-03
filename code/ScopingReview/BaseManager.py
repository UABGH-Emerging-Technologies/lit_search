import re
from abc import abstractmethod

import pandas as pd
import pdfplumber
from aiweb_common.file_operations.docx_creator import FastAPIDocxCreator
from aiweb_common.file_operations.excel_creator import (
    ExcelCreator,
    FastAPIExcelCreator,
)
from aiweb_common.resource.PubMedInterface import PubMedInterface

import ScopingReview_config.app_config as app_config
import ScopingReview_config.config as config


class BaseManager:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @abstractmethod
    def _get_filename(self):
        raise NotImplementedError

    @abstractmethod
    def _get_mime_type(self):
        raise NotImplementedError

    def _check_relevance(self, row):
        """
        This function checks if either Author 1 or Author 2 has marked an article as relevant based on the
        input provided.

        Args:
          row: The `_check_relevance` function takes a `row` parameter, which is expected to be a
        dictionary-like object containing keys "Author 1: Relevant Article? (Yes/No)" and "Author 2:
        Relevant Article? (Yes/No)".

        Returns:
          The `_check_relevance` method returns either the string "True" if either `author1_relevant` or
        `author2_relevant` are True, or it returns None if both `author1_relevant` and `author2_relevant` are
        False.
        """
        author1_relevant = str(row["Author 1: Relevant Article? (Yes/No)"]).lower() in [
            "yes",
            "y",
            "true",
            "t",
        ]
        author2_relevant = str(row["Author 2: Relevant Article? (Yes/No)"]).lower() in [
            "yes",
            "y",
            "true",
            "t",
        ]

        if author1_relevant or author2_relevant:
            return "True"
        else:
            return None

    def write_excel_output(self, tmpfile, df, input_search_terms, query_strings):
        """Write the articles DataFrame plus search-term metadata to an Excel file."""
        ExcelCreator().write_excel_output(
            tmpfile=tmpfile,
            df=df,
            input_search_terms=input_search_terms,
            query_strings=query_strings,
        )

    def get_tempfile_excel(self, articles_df, research_question, pubmed_query):
        """Create a temporary Excel file from the articles DataFrame and return its path."""
        return ExcelCreator().get_tempfile_excel(articles_df, research_question, pubmed_query)

    def get_encoded_excel(
        self, articles_df, background_tasks, research_question="", pubmed_query=""
    ):
        """Encode an Excel file of articles to base64, scheduling temp-file cleanup."""
        encoder = FastAPIExcelCreator(background_tasks)
        return encoder.get_encoded_excel(articles_df, research_question, pubmed_query)

    def get_encoded_docx(self, md_string, background_tasks):
        """
        The function `get_encoded_docx` converts a Markdown string to a DOCX file and returns the file
        as bytes.

        Args:
          md_string: The `md_string` parameter in the `get_encoded_docx` method is a string containing
        the Markdown content that you want to convert to a DOCX file.
          background_tasks: Background_tasks typically refer to tasks that are meant to be executed
        asynchronously or in the background, separate from the main flow of the program. These tasks can
        include things like sending emails, processing large files, or performing time-consuming
        operations without blocking the main thread of execution. In the context of the `get

        Returns:
          The function `get_encoded_docx` is returning the result of converting a Markdown string
        (`md_string`) to a DOCX file in bytes using the `DocxCreator` class and the provided
        `background_tasks`.
        """
        encoder = FastAPIDocxCreator(background_tasks)
        return encoder.convert_markdown_to_docx_bytes(md_string)

    def make_initial_df(self, articles_df):
        """
        The function `make_initial_df` adds columns for author responses and renames the "pmid" column
        to "PMID" in the input DataFrame.

        Args:
          articles_df: The `make_initial_df` function takes an `articles_df` DataFrame as input and
        performs the following operations:

        Returns:
          The function `make_initial_df` is returning the `articles_df` DataFrame after inserting two
        new columns for author responses ("Author 1: Relevant Article? (Yes/No)" and "Author 2: Relevant
        Article? (Yes/No)") with default values "No", and renaming the "pmid" column to "PMID". The
        function also includes a placeholder for adding full text link
        """
        # add author response column
        articles_df.insert(0, "Author 1: Relevant Article? (Yes/No)", "No")
        articles_df.insert(1, "Author 2: Relevant Article? (Yes/No)", "No")

        articles_df.rename(columns={"pmid": "PMID"}, inplace=True)

        # TODO: Wait until after categories are assigned
        # # add full text link and text if available

        return articles_df

    def extract_docx_pmids(self, text):
        """
        The function `extract_docx_pmids` extracts PMIDs (PubMed Identifiers) from a given text and returns
        them as a DataFrame.

        Args:
          text: Please provide the text from which you want to extract the PMIDs.

        Returns:
          The `extract_docx_pmids` function is returning a DataFrame containing the PMIDs (PubMed
          Identifiers) extracted from the input text. The PMIDs are extracted using a regular expression
        pattern that looks for the specific format "PMID: <digits>". The function then returns these
        extracted PMIDs as a DataFrame with a single column named "PMID".
        """
        # Regular expression to find PMIDs
        pattern = r"PMID: (\d+)"

        # Find all PMIDs in the text
        pmids = re.findall(pattern, text)

        # Return as a DataFrame
        return pd.DataFrame(pmids, columns=["PMID"])

    def get_relevant_rows(self):
        """
        The function `get_relevant_rows` processes a pandas DataFrame to identify and return rows that are
        considered relevant based on a custom relevance check.

        Returns:
          The `get_relevant_rows` method returns a pandas DataFrame containing only the rows that are
        considered relevant based on the `_check_relevance` function applied to each row.
        """
        if not isinstance(self.df, pd.DataFrame):
            raise ValueError("Expected input to be a pandas DataFrame")
        self.df["Relevant"] = self.df.apply(self._check_relevance, axis=1)
        relevant_df = self.df.dropna(subset=["Relevant"])
        return relevant_df

    def fetch_full_text(self, pmids, access_token=app_config.LIBKEY_API_KEY):
        """Retrieve full text for the given PMIDs via PMC and LibKey services."""
        return PubMedInterface(email=config.DEV_EMAIL).fetch_full_text(
            pmids, access_token=access_token, library_number=app_config.UAB_LIBKEY_ID
        )

    def extract_text_from_pdf(self, pdf_path):
        """
        The function `extract_text_from_pdf` takes a PDF file path as input, extracts text from each
        page using pdfplumber, and returns the concatenated text from all pages.

        Args:
          pdf_path: The `pdf_path` parameter in the `extract_text_from_pdf` function is the file path to
        the PDF file from which you want to extract text. This function uses the `pdfplumber` library to
        open the PDF file and extract text from each page in the PDF.

        Returns:
          The function `extract_text_from_pdf` returns the extracted text content from the PDF file
        located at the specified `pdf_path`.
        """
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        return text
