import requests
from urllib.request import urlretrieve
from io import BytesIO
import ScopingReview_config.app_config as lit_ap_config
import ScopingReview_config.config as review_config
import pandas as pd
import pdfplumber
from Bio import Entrez
from llm_utils.call_pubmed_api import PubMedAPI
from llm_utils.prep_pubmed_query import PubMedQueryGenerator

# For NCBI interactions
Entrez.email = review_config.DEV_EMAIL
#os.environ['NCBI_API_KEY'] = lit_ap_config.NCBI_API_KEY

#### MAIN Interface Functions ####
def make_and_refine_query(previous_query, research_q, cost, loop_counter):
    query_maker = PubMedQueryGenerator(research_q)
    search_string, response_meta = query_maker.generate_search_string(
        PUBMED_CHAT = review_config.CHAT,
        loop_n=loop_counter, 
        last_query=previous_query
        )
    cost += response_meta.total_cost
    previous_query = search_string
    loop_counter += 1
    return cost, loop_counter, previous_query, search_string

def search_and_compile(query, article_ids=[]):
    pm_connection = PubMedAPI(email=review_config.DEV_EMAIL, max_results=review_config.MAX_ARTICLES_SR, streamlit_context=True)
    article_ids_new = pm_connection.search_pubmed_articles(query)
    article_ids = list(set().union(article_ids, article_ids_new))
    articles_df = pm_connection.fetch_article_details(article_ids)
    return articles_df

def write_excel_output(tmpfile, articles_df, unique_keywords_str):
    with pd.ExcelWriter(tmpfile.name, engine='xlsxwriter') as writer:
        articles_df.to_excel(writer, index=False, sheet_name='Sheet1')
        
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
        for idx, col in enumerate(articles_df.columns):
            # Find the maximum length of data in the column
            column_len = articles_df[col].astype(str).map(len).max()
            column_title_len = len(col)
            max_len = min(100,max(column_len, column_title_len))

            # Set the column width with some extra margin
            worksheet1.set_column(idx, idx, max_len + 1, wrap_format)
    
        # You can also set column width for the second sheet if needed
        worksheet2.set_column(0, 0, len('Unique Keywords') + 1, wrap_format)
        
#### Step 2 - Iteration functions ####
# Function to check if either of the values is a 'Yes'
def check_relevance(row):
    author1_relevant = str(row["Author 1: Relevant Article? (Yes/No)"]).lower() in ["yes", "y", "true", "t"]
    author2_relevant = str(row["Author 2: Relevant Article? (Yes/No)"]).lower() in ["yes", "y", "true", "t"]

    if author1_relevant or author2_relevant:
        return row['keywords']
    else:
        return None

def get_relevant_keywords(df):
    df['Relevant Keywords'] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=['Relevant Keywords'])
    return relevant_df

def get_unique_keywords(df):
    df['Relevant Keywords'] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=['Relevant Keywords'])

    # Join all keywords into a single string, then split by comma
    all_keywords = ",".join(relevant_df['Relevant Keywords']).split(',')

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

def get_libkey_text_link(pubmed_id, access_token=lit_ap_config.LIBKEY_API_KEY, library_number=lit_ap_config.UAB_LIBKEY_ID):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3'
    }
    api_url = f"https://public-api.thirdiron.com/public/v1/libraries/{library_number}/articles/pmid/{pubmed_id}?access_token={access_token}"
    response = requests.get(api_url, headers=headers, timeout=5)
    if response.status_code == 200:
        data = response.json()
        return data['data']['fullTextFile']
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
    data = {'PMID': [], 'URL': [], 'Downloaded': [], 'Text': []}

    pmcids = get_pmcids_from_pubmed(pmids)
    print(pmcids)

    for pmid, pmcid in zip(pmids, pmcids):
        print(pmid)
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
                # Check if LibKey provides a direct PDF link
                libkey_url = get_libkey_text_link(pmid, access_token)
                if libkey_url and libkey_url.endswith('.pdf'):
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3'
                        }
                        response = requests.get(libkey_url, timeout=20, headers=headers)
                        if response.ok:
                            text = extract_text_from_pdf_bytes(response.content)
                            url = libkey_url
                            downloaded = True
                    except Exception as e:
                        print(f"Error during LibKey PDF download for PMID {pmid}: {e}")
                else:
                    url = libkey_url  # Record the URL provided by LibKey, even if not a direct PDF

        except Exception as e:
            print(f"Error during processing PMID {pmid}: {e}")

        data['PMID'].append(pmid)
        data['URL'].append(url if url else "Not available")
        data['Downloaded'].append(downloaded)
        data['Text'].append(text if text else "Text not available")

    return pd.DataFrame(data)


def make_initial_df(pm_connection, article_ids):
    articles_df = pm_connection.fetch_article_details(article_ids)
    
    # add author response column
    articles_df.insert(0, 'Author 1: Relevant Article? (Yes/No)', 'No')  
    articles_df.insert(1, 'Author 2: Relevant Article? (Yes/No)', 'No')  
    
    articles_df.rename(columns={'pmid': 'PMID'}, inplace=True)
    
    # TODO: Wait until after categories are assigned
    # # add full text link and text if available
    # full_text_df = fetch_full_text(articles_df.PMID)
    # articles_df = pd.merge(articles_df, full_text_df, on="PMID", how="inner")
    
    return articles_df

# Example usage
# pmids = ["32076685","23376664","38289217","30995704","16178450","31562971","32242448","16934734","18893366","24880802","9952101","29342391","18354149","25587612", "8014946"]
# access_token = 
# full_text_df = fetch_full_text(pmids, access_token)
# full_text_df.to_excel("/data/test_with_urls.xlsx")

    