import pandas as pd
import re

import ScopingReview_config.config as config
import ScopingReview_config.app_config as app_config
import streamlit as st
import pdfplumber
from abc import abstractmethod
from Bio import Entrez
import xml.etree.ElementTree as ET


import requests
from io import BytesIO

class BaseManager():
    def __init__(self, df:pd.DataFrame):
        self.df = df

    @abstractmethod      
    def _get_filename(self):
        raise NotImplementedError   
    
    @abstractmethod
    def _get_mime_type(self):
        raise NotImplementedError
    
    def write_search_excel_output(self, tmpfile, df, input_search_terms, query_strings=""):
        with pd.ExcelWriter(tmpfile.name, engine="xlsxwriter") as writer:
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
            
    def write_keywords_excel_output(self, tmpfile, df, unique_keywords_str):
        with pd.ExcelWriter(tmpfile.name, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            # Convert string to dataFrame and save to excel
            df_keywords = pd.DataFrame([unique_keywords_str], columns=['Unique Keywords'])
            df_keywords.to_excel(writer, index=False, sheet_name='Sheet2')

            # Get the xlsxwriter workbook and worksheet objects
            workbook  = writer.book
            worksheet1 = writer.sheets['Sheet1']
            worksheet2 = writer.sheets['Sheet2']
            # Define a format with word wrap
            wrap_format = workbook.add_format({'text_wrap': True})

            # Iterate over the DataFrame columns to set the column width
            for idx, col in enumerate(df.columns):
                # Find the maximum length of data in the column
                column_len = df[col].astype(str).map(len).max()
                column_title_len = len(col)
                max_len = min(100,max(column_len, column_title_len))

                # Set the column width with some extra margin
                worksheet1.set_column(idx, idx, max_len + 1, wrap_format)
        
            # You can also set column width for the second sheet if needed
            worksheet2.set_column(0, 0, len('Unique Keywords') + 1, wrap_format)
            
    def get_relevant_rows(self):
        if not isinstance(self.df, pd.DataFrame):
            raise ValueError("Expected input to be a pandas DataFrame")
        self.df["Relevant"] = self.df.apply(self._check_relevance, axis=1)
        relevant_df = self.df.dropna(subset=["Relevant"])
        return relevant_df
    
    def _check_relevance(self, row):
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
        
    def fetch_full_text(self, pmids, access_token= app_config.LIBKEY_API_KEY):
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

    def _get_pmcid_from_pubmed(self, pmid):
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
        text = ""
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def _download_pmc_pdf(self, pmcid):
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

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        return text

    def extract_docx_pmids(self, text):
        pattern = r"PMID: (\d+)"

        pmids = re.findall(pattern, text)

        return pd.DataFrame(pmids, columns=["PMID"])
