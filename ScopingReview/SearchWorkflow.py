import os
import pdfplumber
from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from ScopingReview_config import config, prompt_config
from aiweb_common.resource.PubMedInterface import PubMedInterface
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
import pandas as pd
import json
import re
import xml.etree.ElementTree as ET
from io import BytesIO
import requests
from Bio import Entrez

Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = config.NCBI_API_KEY

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.article_ids = []
        self.research_question = research_question

    def _make_initial_df(self, pubmed_connection, article_ids):
        articles_df = pubmed_connection.fetch_article_details(article_ids)

        # add author response column
        articles_df.insert(0, "Author 1: Relevant Article? (Yes/No)", "No")
        articles_df.insert(1, "Author 2: Relevant Article? (Yes/No)", "No")

        articles_df.rename(columns={"pmid": "PMID"}, inplace=True)

        return articles_df
    
    def _search_and_compile(self, query):
        pubmed_connection = PubMedInterface(
            email=config.DEV_EMAIL,
            max_results=config.MAX_ARTICLES_SR,
            streamlit_context=True,
        )
        print("query - ",query)
        article_ids_new = pubmed_connection.search_pubmed_articles(query)
        print(article_ids_new)
        article_ids = list(set().union(self.article_ids, article_ids_new))
        articles_df = self._make_initial_df(pubmed_connection, article_ids)
        return articles_df
    
    def write_excel_output(tmpfile, df, input_search_terms, query_strings=""):
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

    def process(self):
        # Gather references from PubMed
        single_response = SingleResponseHandler(config.LLM_INTERFACE)
        
        print('Assembling prompts')
        assembled_prompt = single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.PUBMED_SYSTEM_PROMPT,
            user_prompt=prompt_config.PUBMED_HUMAN_PROMPT,
            text=self.research_question
        )
        
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        articles_df = self._search_and_compile(response.content)
        return articles_df


    def make_and_refine_query(previous_query, research_q, loop_counter):
        query_maker = PubMedQueryGenerator(research_q)
        search_string, response_meta = query_maker.generate_search_string(
            PUBMED_CHAT=config.LLM_INTERFACE, loop_n=loop_counter, last_query=previous_query
        )
        cost = response_meta.total_cost
        previous_query = search_string
        loop_counter += 1
        return cost, loop_counter, previous_query, search_string

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
