from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import requests
from urllib.request import urlretrieve
import os 
from io import BytesIO
# import ScopingReview_config.app_config as lit_ap_config
import ScopingReview.prompts as prompt
import pandas as pd
import pdfplumber
import base64
import tempfile
import time
from Bio import Entrez

# For NCBI interactions
Entrez.email = "rmelvin@uabmc.edu"
# os.environ['NCBI_API_KEY'] = lit_ap_config.NCBI_API_KEY

def get_pmcid_from_pubmed(pmid):
    link_result = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
    record = Entrez.read(link_result)
    try:
        pmcid = record[0]['LinkSetDb'][0]['Link'][0]['Id']
        return pmcid
    except (IndexError, KeyError):
        return None

def get_pmcids_from_pubmed(pmids):
    pmcids = []
    for pmid in pmids:
        pmcid = get_pmcid_from_pubmed(pmid)
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

# def get_libkey_text_link(pubmed_id, access_token=lit_ap_config.LIBKEY_API_KEY, library_number=lit_ap_config.UAB_LIBKEY_ID):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3'
#     }
#     api_url = f"https://public-api.thirdiron.com/public/v1/libraries/{library_number}/articles/pmid/{pubmed_id}?access_token={access_token}"
#     response = requests.get(api_url, headers=headers, timeout=5)
#     if response.status_code == 200:
#         data = response.json()
#         return data['data']['fullTextFile']
#     else:
#         print(f"Error fetching data: {response.status_code}")
#         return None

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

        
# def fetch_full_text(pmids, access_token=lit_ap_config.LIBKEY_API_KEY):
#     data = {'PMID': [], 'URL': [], 'Downloaded': [], 'Text': []}

#     pmcids = get_pmcids_from_pubmed(pmids)
#     print(pmcids)

#     for pmid, pmcid in zip(pmids, pmcids):
#         print(pmid)
#         url = None
#         downloaded = False
#         text = None

#         try:
#             if pmcid:
#                 url, text = download_pmc_pdf(pmcid)
#                 if text:
#                     downloaded = True
#                 else:
#                     print(f"Failed to download or process PDF from PMC for PMID {pmid}")

#             if not downloaded:
#                 # Check if LibKey provides a direct PDF link
#                 libkey_url = get_libkey_text_link(pmid, access_token)
#                 if libkey_url and libkey_url.endswith('.pdf'):
#                     try:
#                         headers = {
#                             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3'
#                         }
#                         response = requests.get(libkey_url, timeout=20, headers=headers)
#                         if response.ok:
#                             text = extract_text_from_pdf_bytes(response.content)
#                             url = libkey_url
#                             downloaded = True
#                     except Exception as e:
#                         print(f"Error during LibKey PDF download for PMID {pmid}: {e}")
#                 else:
#                     url = libkey_url  # Record the URL provided by LibKey, even if not a direct PDF

#         except Exception as e:
#             print(f"Error during processing PMID {pmid}: {e}")

#         data['PMID'].append(pmid)
#         data['URL'].append(url if url else "Not available")
#         data['Downloaded'].append(downloaded)
#         data['Text'].append(text if text else "Text not available")

#     return pd.DataFrame(data)
  
  
def categorization(df, input_text):
  input_list = input_text.split(',')
  input_list = [value.strip() for value in input_list if value.strip()]

  for index, row in df.iterrows():
      data = row['abstract']
      result = prompt.CHAT.invoke(prompt.categorization_chat_prompt.format_prompt(categories=input_list, context=data).to_messages())
      df.at[index, 'category'] = result.content
    
  print(df['category'])
      
  return df
  
# Example usage
# pmids = ["32076685","23376664","38289217","30995704","16178450","31562971","32242448","16934734","18893366","24880802","9952101","29342391","18354149","25587612", "8014946"]
# access_token = 
# full_text_df = fetch_full_text(pmids, access_token)
# full_text_df.to_excel("/data/test_with_urls.xlsx")