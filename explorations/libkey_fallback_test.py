from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from urllib.request import urlretrieve
import os 
os.environ['NCBI_API_KEY'] = "5c7b745fcba4a835c311c056f725c6814208"
from Bio import Entrez
Entrez.email = "rmelvin@uabmc.edu"

def get_pmcid_from_pubmed(pmid):
    link_result = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
    record = Entrez.read(link_result)
    try:
        pmcid = record[0]['LinkSetDb'][0]['Link'][0]['Id']
        return pmcid
    except (IndexError, KeyError):
        return None

def get_pdf_url(pmcid):
    url = f"http://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmcid}&blobtype=pdf"
    # even though we're using the europe one, should we present the american one to the user?
    # url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf"
    response = requests.get(url, allow_redirects=True)
    final_url = response.url
    return final_url


def get_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        # Mimic non-headless user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set window size when running headless
    #chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=9222")
    # Set a user agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_full_text_link(pubmed_id, access_token):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    api_url = f"https://public-api.thirdiron.com/public/v1/libraries/731/articles/pmid/{pubmed_id}?access_token={access_token}"
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['data']['fullTextFile']
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def download_pdf_with_selenium(pubmed_id, access_token, headless=True):
    full_text_link = get_full_text_link(pubmed_id, access_token)
    if full_text_link:
        driver = get_driver(headless=headless)
        driver.get(full_text_link)

        # Add an explicit wait for a condition
        try:
            WebDriverWait(driver, 20).until(EC.url_contains(".pdf"))
        except TimeoutException:
            print("Timed out waiting for PDF URL.")

        final_url = driver.current_url
        print(f"Final URL: {final_url}")

        if final_url.endswith('.pdf'):
            local_filename = f"{pubmed_id}.pdf"
            urlretrieve(final_url, local_filename)
            print(f"PDF saved as {local_filename}")
        else:
            print("The final URL is not a PDF.")
        driver.quit()

    else:
        print("Unable to retrieve full text link.")
        
def fetch_pdf(pmid, access_token):
    try:
        pmcid = get_pmcid_from_pubmed(pmid)
        if pmcid:
            pdf_url = get_pdf_url(pmcid)
            if pdf_url:
                print(pdf_url)
                urlretrieve(pdf_url, f'{pmid}.pdf')
                print(f"PDF saved as {pmid}.pdf using PMC")
                return
    except Exception as e:
        print(f"Error during PMC download: {e}")
    # Fallback to Selenium method if PMC download fails
    try:
        download_pdf_with_selenium(pmid, access_token)
    except TimeoutException:
        print("Failed to download PDF using Selenium.")


# Example usage
access_token = "56e085ab-387b-4696-8583-762fa32ab29b"
pubmed_id = "38365899"
fetch_pdf(pubmed_id, access_token)

#NOTES:
# So let's have the first csv provide the full text links
# and if it comes from pmc OR libkey resolves to something ending in ".pdf",
# we'll say we can get the pdf
