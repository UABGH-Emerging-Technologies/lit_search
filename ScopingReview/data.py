import json
import os
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.request import urlretrieve

import pandas as pd
import pdfplumber
import requests
from Bio import Entrez
from llm_utils.call_pubmed_api import PubMedAPI
from llm_utils.prep_pubmed_query import PubMedQueryGenerator

import ScopingReview_config.app_config as lit_ap_config
import ScopingReview_config.config as lit_config
import streamlit as st

try:
    from llm_utils.database import get_db_connection
except ImportError:
    print("Database prereqs not installed. This is expected if you are not in a streamlit context.")

# For NCBI interactions
Entrez.email = lit_config.DEV_EMAIL
# This is the only way to set the key in the packages we use :(
os.environ["NCBI_API_KEY"] = lit_ap_config.NCBI_API_KEY


def parse_keywords(content):
    # Load the JSON string into a Python dictionary
    data = json.loads(content)

    # Extract keyword lists into variables
    primary_keywords = data.get("Primary Keywords", [])
    secondary_keywords = data.get("Secondary Keywords", [])
    exclusion_keywords = data.get("Exclusion Keywords", [])

    return primary_keywords, secondary_keywords, exclusion_keywords


#### MAIN Interface Functions ####
def make_and_refine_query(previous_query, research_q, loop_counter):
    query_maker = PubMedQueryGenerator(research_q)
    search_string, response_meta = query_maker.generate_search_string(
        PUBMED_CHAT=lit_config.LLM_INTERFACE, loop_n=loop_counter, last_query=previous_query
    )
    cost = response_meta.total_cost
    previous_query = search_string
    loop_counter += 1
    return cost, loop_counter, previous_query, search_string


def search_and_compile(query, article_ids=[]):
    pm_connection = PubMedAPI(
        email=lit_config.DEV_EMAIL,
        max_results=lit_config.MAX_ARTICLES_SR,
        streamlit_context=True,
    )
    print(query)
    article_ids_new = pm_connection.search_pubmed_articles(query)
    print(article_ids_new)
    article_ids = list(set().union(article_ids, article_ids_new))
    return pm_connection, article_ids


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


#### Step 2 - Iteration functions ####
# Function to check if either of the values is a 'Yes'
def check_relevance(row):
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


def get_relevant_rows(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Expected input to be a pandas DataFrame")
    df["Relevant"] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=["Relevant"])
    return relevant_df


def clean_title(title):
    title = (
        title.strip()
        .replace("'", "")
        .replace("*", "")
        .replace("[", "")
        .replace("]", "")
        .replace("/", ", ")
        .replace("&", "and")
    )
    return title


def clean_keywords(keywords):
    cleaned_keywords = []
    for keyword in keywords:
        # Remove surrounding single quotes and extra whitespace
        keyword = (
            keyword.strip()
            .replace("'", "")
            .replace("*", "")
            .replace("[", "")
            .replace("]", "")
            .replace("/", ", ")
            .replace("&", "")
        )
        cleaned_keywords.append(keyword)

    # no need to join the cleaned keywords with commas as they are already separate keywords
    return cleaned_keywords


def get_unique_keywords(df):
    # TODO fix issue regarding warning here:
    #  A value is trying to be set on a copy of a slice from a DataFrame.
    # Try using .loc[row_indexer,col_indexer] = value instead
    df["Relevant"] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=["Relevant"])

    # Join all keywords into a single string, then split by comma
    all_keywords = ",".join(relevant_df["keywords"]).split(",")

    # Remove leading/trailing white spaces and convert to lower case
    all_keywords = [keyword.strip().lower() for keyword in all_keywords]

    # Get unique keywords
    unique_keywords = list(set(all_keywords))
    # Convert list of unique keywords to a comma-separated string
    unique_keywords_str = ", ".join(unique_keywords)

    return unique_keywords_str


#### Step 3 - Retrieve full text functions ####


# Should some of these go into the pubmed api class (or similar new class) in LLM Utils?
def get_pmcid_from_pubmed(pmid):
    # from https://www.biostars.org/p/321100/
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
            pmcid = get_pmcid_from_pubmed(pmid)
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
        text = extract_text_from_pdf_bytes(response.content)
        return final_url, text
    except Exception as e:
        print(f"Failed to retrieve or process PDF for PMCID {pmcid}: {e}")
        return None, None


def get_libkey_text_link(
    pubmed_id, access_token=lit_ap_config.LIBKEY_API_KEY, library_number=lit_ap_config.UAB_LIBKEY_ID
):
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


def fetch_full_text(pmids, access_token=lit_ap_config.LIBKEY_API_KEY):
    data = {"PMID": [], "URL": [], "Downloaded": [], "Text": []}

    pmcids = get_pmcids_from_pubmed(pmids)

    for pmid, pmcid in zip(pmids, pmcids):
        url = None
        downloaded = False
        text = None

        try:
            if pmcid:
                url, text = download_pmc_pdf(pmcid)
                if text:
                    downloaded = True
                else:
                    print(f"Failed to download or process PDF from PMC for PMID {pmid}")

            if not downloaded:
                # Check if LibKey provides link to full text
                try:
                    libkey_url = get_libkey_text_link(pmid, access_token)
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


def make_initial_df(pm_connection, article_ids):
    articles_df = pm_connection.fetch_article_details(article_ids)

    # add author response column
    articles_df.insert(0, "Author 1: Relevant Article? (Yes/No)", "No")
    articles_df.insert(1, "Author 2: Relevant Article? (Yes/No)", "No")

    articles_df.rename(columns={"pmid": "PMID"}, inplace=True)

    # TODO: Wait until after categories are assigned
    # # add full text link and text if available

    return articles_df


def extract_docx_pmids(text):
    # Regular expression to find PMIDs
    pattern = r"PMID: (\d+)"

    # Find all PMIDs in the text
    pmids = re.findall(pattern, text)

    # Return as a DataFrame
    return pd.DataFrame(pmids, columns=["PMID"])


def write_to_db(research_q, query_type, input_time, response_time, cost):
    try:
        with get_db_connection(
            db_server=lit_ap_config.DB_SERVER,
            db_name=lit_ap_config.DB_NAME,
            db_user=lit_ap_config.DB_USER,
            db_password=lit_ap_config.DB_PASSWORD,
        ) as conn:
            # tempting to move this into llm_utils, but the query will be unique to each app.
            cursor = conn.cursor()
            query = """
                    INSERT INTO [dbo].[literature_helper] (
                        research_idea, 
                        purpose_request, 
                        input_time, 
                        response_time,
                        total_cost
                    ) VALUES (?, ?, ?, ?, ?)
                    """

            cursor.execute(query, (research_q, query_type, input_time, response_time, cost))
        st.success(
            "To comply with a Health System Information Security request, submissions are recorded for potential review."
        )
    except Exception as e:
        st.error(
            "Something went wrong, and your submission was not recorded for review. Give the following message when asking for help."
        )
        st.error(e)
