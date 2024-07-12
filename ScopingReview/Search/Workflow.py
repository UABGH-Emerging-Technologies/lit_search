import os
import pdfplumber
from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from ScopingReview_config import config, prompt_config
from aiweb_common.resource.PubMedInterface import PubMedInterface
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
import pandas as pd

import re
import xml.etree.ElementTree as ET
from io import BytesIO
import requests
from Bio import Entrez

from ScopingReview.SearchManager import (
    ArticleSearchManager,
    IterateSearchManager,
    NewsletterSearchManager,
    FastAPISearchManager,
    FastAPIIterateSearchManager,
)

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = config.NCBI_API_KEY

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question
        self.search_manager = ArticleSearchManager(scoping_step=None, research_q=research_question)

    def process(self):
        query_generator = PubMedQueryGenerator(config.LLM_INTERFACE, self.research_question)
        pubmed_interface = PubMedInterface()
        n=0
        while n <= config.MAX_TRIES:
            print('Generating PubMed Query')
            search_string = query_generator.generate_search_string()
            print("QUERY - ", search_string)
            article_ids = pubmed_interface.search_pubmed_articles(search_string)
            if len(article_ids>config.MIN_ARTICLES):
                articles_df = pubmed_interface.fetch_article_details(article_ids)
            else:
                n=n+1
                    
        articles_df = self.search_manager.search_and_compile_articles()
        return articles_df

    def get_pmcid_from_pubmed(pmid):
        handle = Entrez.elink(dbfrom="pubmed", db="pmc", linkname="pubmed_pmc", id=pmid, retmode="text")

        handle_read = handle.read()
        handle.close()

        root = ET.fromstring(handle_read)

        pmcid = ""

        for link in root.iter("Link"):
            for id in link.iter("Id"):
                pmcid = id.text
        return pmcid

    def get_pmcids_from_pubmed(pmids):
        pmcids = []
        for pmid in pmids:
            try:
                pmcid = ArticleSearch.get_pmcid_from_pubmed(pmid)
            except Exception as e:
                print(f"Second attempt failed to retrieve PMCID {pmid}: {e}")
                pmcid = ""
            pmcids.append(pmcid)
        return pmcids

    def extract_text_from_pdf_bytes(pdf_bytes):
        text = ""
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def download_pmc_pdf(pmcid):
        url = f"http://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmcid}&blobtype=pdf"
        try:
            response = requests.get(url, allow_redirects=True)
            final_url = response.url
            text = ArticleSearch.extract_text_from_pdf_bytes(response.content)
            return final_url, text
        except Exception as e:
            print(f"Failed to retrieve or process PDF for PMCID {pmcid}: {e}")
            return None, None

    def get_libkey_text_link(pubmed_id, access_token=config.LIBKEY_API_KEY, library_number=config.UAB_LIBKEY_ID):
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

    def extract_text_from_pdf(pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        return text

    def fetch_full_text(pmids, access_token=config.LIBKEY_API_KEY):
        data = {"PMID": [], "URL": [], "Downloaded": [], "Text": []}

        pmcids = ArticleSearch.get_pmcids_from_pubmed(pmids)

        for pmid, pmcid in zip(pmids, pmcids):
            url = None
            downloaded = False
            text = None

            try:
                if pmcid:
                    url, text = ArticleSearch.download_pmc_pdf(pmcid)
                    if text:
                        downloaded = True
                    else:
                        print(f"Failed to download or process PDF from PMC for PMID {pmid}")

                if not downloaded:
                    try:
                        libkey_url = ArticleSearch.get_libkey_text_link(pmid, access_token)
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

    def extract_docx_pmids(text):
        pattern = r"PMID: (\d+)"

        pmids = re.findall(pattern, text)

        return pd.DataFrame(pmids, columns=["PMID"])
