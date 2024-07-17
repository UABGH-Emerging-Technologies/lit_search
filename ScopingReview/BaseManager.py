import pandas as pd
import re
import os
import ScopingReview_config.config as config
import ScopingReview_config.app_config as app_config
import streamlit as st
import pdfplumber
from abc import abstractmethod
from Bio import Entrez
import xml.etree.ElementTree as ET
from aiweb_common.file_operations.file_handling import file_to_base64
from aiweb_common.file_operations.DocxCreator import DocxCreator

import tempfile


import requests
from io import BytesIO


# This Python class provides methods for managing dataframes, writing Excel outputs, fetching full
# text articles, and extracting information from PDFs.
class BaseManager():
    def __init__(self, df:pd.DataFrame):
        self.df = df

    @abstractmethod      
    def _get_filename(self):
        raise NotImplementedError   
    
    @abstractmethod
    def _get_mime_type(self):
        raise NotImplementedError
    
    def _get_pmcid_from_pubmed(self, pmid):
        """
        This Python function retrieves the PMC ID associated with a given PubMed ID using Entrez and
        ElementTree.
        
        Args:
          pmid: The function `_get_pmcid_from_pubmed` takes a PubMed ID (pmid) as input and retrieves
        the corresponding PMC ID (pmcid) by querying the Entrez database. The function uses the Entrez
        module from Biopython to perform the query.
        
        Returns:
          The function `_get_pmcid_from_pubmed` returns the PMC ID (PubMed Central ID) associated with a
        given PubMed ID (PMID).
        """
        handle = Entrez.elink(dbfrom="pubmed", db="pmc", linkname="pubmed_pmc", id=pmid, retmode="text")

        handle_read = handle.read()
        handle.close()

        root = ET.fromstring(handle_read)

        pmcid = ""

        for link in root.iter("Link"):
            for id in link.iter("Id"):
                pmcid = id.text
        return pmcid

    def _get_pmcids_from_pubmed(self, pmids):
        """
        The function `_get_pmcids_from_pubmed` retrieves PMCIDs from PubMed given a list of PMIDs,
        handling exceptions gracefully.
        
        Args:
          pmids: The `pmids` parameter in the `_get_pmcids_from_pubmed` function is a list of PubMed IDs
        (PMIDs) that you want to convert to PubMed Central IDs (PMCIDs). The function iterates over each
        PMID in the list, attempts to retrieve the corresponding PMCID using
        
        Returns:
          The function `_get_pmcids_from_pubmed` returns a list of PMCIDs corresponding to the input
        list of PMIDs. If an exception occurs while trying to retrieve a PMCID for a specific PMID, an
        empty string is appended to the list of PMCIDs for that PMID.
        """
        pmcids = []
        for pmid in pmids:
            try:
                pmcid = self._get_pmcid_from_pubmed(pmid)
            except Exception as e:
                print(f"Second attempt failed to retrieve PMCID {pmid}: {e}")
                pmcid = ""
            pmcids.append(pmcid)
        return pmcids

    def _extract_text_from_pdf_bytes(self, pdf_bytes):
        """
        This function extracts text from a PDF file given its bytes using the pdfplumber library in
        Python.
        
        Args:
          pdf_bytes: The `pdf_bytes` parameter in the `_extract_text_from_pdf_bytes` function is
        expected to be a byte string containing the content of a PDF file. This function reads the PDF
        content from the byte string using the `pdfplumber` library and extracts text from each page of
        the PDF file.
        
        Returns:
          The function `_extract_text_from_pdf_bytes` returns the extracted text content from the PDF
        file represented by the input `pdf_bytes`.
        """
        text = ""
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def _download_pmc_pdf(self, pmcid):
        """
        The function `_download_pmc_pdf` downloads a PDF file from a specified URL and extracts text
        from the downloaded PDF content.
        
        Args:
          pmcid: The `pmcid` parameter in the `_download_pmc_pdf` function is a unique identifier for a
        PubMed Central (PMC) article. It is used to construct the URL for downloading the PDF file of
        the article from the Europe PMC website.
        
        Returns:
          The function `_download_pmc_pdf` returns a tuple containing the final URL of the PDF and the
        extracted text from the PDF. If there is an exception during the process, it returns `None,
        None`.
        """
        url = f"http://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmcid}&blobtype=pdf"
        try:
            response = requests.get(url, allow_redirects=True)
            final_url = response.url
            text = self._extract_text_from_pdf_bytes(response.content)
            return final_url, text
        except Exception as e:
            print(f"Failed to retrieve or process PDF for PMCID {pmcid}: {e}")
            return None, None

    def _get_libkey_text_link(self, pubmed_id, access_token=app_config.LIBKEY_API_KEY, library_number=app_config.UAB_LIBKEY_ID):
        """
        This Python function retrieves a full text link for a publication using a given PubMed ID and a
        library API key.
        
        Args:
          pubmed_id: The `pubmed_id` parameter in the `_get_libkey_text_link` function is the unique
        identifier for a publication in the PubMed database. It is used to retrieve information about a
        specific article from the PubMed database.
          access_token: The `access_token` parameter in the `_get_libkey_text_link` function is used to
        provide the API key for accessing the LibKey API. In the code snippet you provided, the
        `access_token` parameter has a default value `app_config.LIBKEY_API_KEY`, which suggests that
        the
          library_number: The `library_number` parameter in the `_get_libkey_text_link` function refers
        to the unique identifier of the library from which you want to retrieve the full text link for a
        specific article identified by its PubMed ID (`pubmed_id`). In this case, the `library_number`
        parameter is set
        
        Returns:
          the full text link of an article based on the PubMed ID using the LibKey API. If the request
        is successful (status code 200), it returns the full text file link. If there is an error
        (status code other than 200), it prints an error message and returns None.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3"
        }
        api_url = f"https://public-api.thirdiron.com/public/v1/libraries/{library_number}/articles/pmid/{pubmed_id}?access_token={access_token}"
        response = requests.get(api_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["data"]["fullTextFile"]
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
        
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
        `author2_relevant` is True, or it returns None if both `author1_relevant` and `author2_relevant` are
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
                    
    # TODO: split up and consider moving functionality to aiweb_common
    def write_excel_output(self, tmpfile, df, input_search_terms, query_strings):
        """
        This Python function writes data from a DataFrame to an Excel file with specific formatting for
        column widths and sheet names.
        
        Args:
          tmpfile: The `tmpfile` parameter in the `write_excel_output` function is the path to the
        temporary Excel file that will be created and written to. This file will contain the data from
        the DataFrame `df`, along with additional information such as `input_search_terms` and
        `query_strings` in a
          df: The `df` parameter in the `write_excel_output` function is a pandas DataFrame containing
        the data that you want to write to an Excel file. This DataFrame will be written to the first
        sheet ("Sheet1") of the Excel file.
          input_search_terms: The `input_search_terms` parameter in the `write_excel_output` function is
        a list of search terms that are used as input for a search query. These search terms are then
        written to the Excel file in the "Input Terms" column of the "Sheet2" worksheet.
          query_strings: The `query_strings` parameter in the `write_excel_output` function is used to
        store the search queries related to the input search terms. These queries are then saved in a
        separate sheet named "Sheet2" in the Excel file generated by the function.
        """
        print("Writing excel file! tempfile - ", tmpfile)

        with pd.ExcelWriter(tmpfile, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")

            # Convert string to dataFrame and save to excel
            data = {"Input Terms": [input_search_terms], "PubMed Querey": [query_strings]}
            df_keywords = pd.DataFrame(data)
            df_keywords.to_excel(writer, index=False, sheet_name="Sheet2")

            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet1 = writer.sheets["Sheet1"]
            worksheet2 = writer.sheets["Sheet2"]
            # Define a format with word wrap
            wrap_format = workbook.add_format({"text_wrap": True})

            # Iterate over the DataFrame columns to set the column width
            for idx, col in enumerate(df.columns):
                # Find the maximum length of data in the column
                column_len = df[col].astype(str).map(len).max()
                column_title_len = len(col)
                max_len = min(100, max(column_len, column_title_len))

                # Set the column width with some extra margin
                worksheet1.set_column(idx, idx, max_len + 1, wrap_format)

            # You can also set column width for the second sheet if needed
            worksheet2.set_column(0, 0, len("Unique Keywords") + 1, wrap_format)
            print("END OF WRITE_SEACRH_EXCEL_OUTPUT")
            
    def get_tempfile_excel(self, articles_df, research_question, pubmed_query):
        """
        The function creates a temporary Excel file containing data from a DataFrame and returns the
        file path.
        
        Args:
          articles_df: articles_df is a pandas DataFrame containing the articles data that you want to
        write to an Excel file.
          research_question: Research question or topic for which the articles were searched.
          pubmed_query: Pubmed query is a search query that is used to retrieve relevant articles from
        the PubMed database. It typically consists of keywords, phrases, and operators that help narrow
        down the search results to find articles related to a specific topic or research question.
        
        Returns:
          The function `get_tempfile_excel` is returning the name of the temporary Excel file that was
        created and written to in the function.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            self.write_excel_output(
                tmpfile=tmpfile.name,
                df=articles_df,
                input_search_terms=research_question,
                query_strings=pubmed_query
                )
        return tmpfile.name
    
    def get_encoded_excel(self, articles_df, background_tasks, research_question="", pubmed_query=""):
        """
        This function encodes an Excel file containing articles data into base64 format and returns the
        encoded file while also adding a task to delete the temporary Excel file.
        
        Args:
          articles_df: The `articles_df` parameter is likely a DataFrame containing data related to
        articles, such as article titles, authors, publication dates, abstracts, etc. It is used as
        input to generate a temporary Excel file that will be encoded to base64 format and returned.
          background_tasks: The `background_tasks` parameter in the `get_encoded_excel` function seems
        to be a task queue or background job manager that allows you to schedule and run tasks
        asynchronously in the background. In this function, it is used to add a task to delete the
        temporary Excel file (`articles_file`) after encoding
          research_question: The `get_encoded_excel` function takes in several parameters:
          pubmed_query: The `pubmed_query` parameter is a string that represents a query that can be
        used to search for articles on PubMed, a free search engine accessing primarily the MEDLINE
        database of references and abstracts on life sciences and biomedical topics. This query can be
        used to filter and retrieve specific articles related to
        
        Returns:
          The function `get_encoded_excel` returns the encoded content of an Excel file generated from
        the `articles_df` DataFrame.
        """
        articles_file = self.get_tempfile_excel(articles_df, research_question, pubmed_query)
        encoded_file = file_to_base64(articles_file)
        background_tasks.add_task(os.unlink, articles_file)
        return encoded_file

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
        encoder = DocxCreator(background_tasks)
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
        
    def fetch_full_text(self, pmids, access_token= app_config.LIBKEY_API_KEY):
        """
        The `fetch_full_text` function retrieves full text articles based on PubMed IDs, utilizing PMC and
        LibKey services.
        
        Args:
          pmids: PMIDs are unique identifiers assigned to scientific journal articles in the PubMed
        database. They are used to easily reference and retrieve specific articles.
          access_token: The `access_token` parameter in the `fetch_full_text` method is used to provide an
        access token for the LibKey API. This token is necessary for accessing the LibKey service to
        retrieve full-text links for the given PubMed IDs (PMIDs). The default value for `access_token` is
        
        Returns:
          The `fetch_full_text` method returns a pandas DataFrame containing information about the full text
        availability for the provided PMIDs. The DataFrame has columns for PMID, URL, Downloaded (boolean
        indicating if the text was successfully downloaded), and Text (the actual text content if available,
        or a message indicating text not available).
        """
        data = {"PMID": [], "URL": [], "Downloaded": [], "Text": []}

        pmcids = self._get_pmcids_from_pubmed(pmids)

        for pmid, pmcid in zip(pmids, pmcids):
            url = None
            downloaded = False
            text = None

            try:
                if pmcid:
                    url, text = self._download_pmc_pdf(pmcid)
                    if text:
                        downloaded = True
                    else:
                        print(f"Failed to download or process PDF from PMC for PMID {pmid}")

                if not downloaded:
                    # Check if LibKey provides link to full text
                    try:
                        libkey_url = self._get_libkey_text_link(pmid, access_token)
                        url = libkey_url
                    except Exception as e:
                        print(f"No libkey url for PMID {pmid}: {e}")
            except Exception as e:
                print(f"Error during processing PMID {pmid}: {e}")

            data["PMID"].append(pmid)
            data["URL"].append(url if url else "Not available")
            data["Downloaded"].append(downloaded)
            data["Text"].append(text if text else "Text not available")

        return pd.DataFrame(data)

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
