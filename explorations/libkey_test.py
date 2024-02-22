from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time

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
            response = requests.get(final_url)
            with open(f'{pubmed_id}.pdf', 'wb') as file:
                file.write(response.content)
            print(f"PDF saved as {pubmed_id}.pdf")
        else:
            print("The final URL is not a PDF.")
        driver.quit()

    else:
        print("Unable to retrieve full text link.")


# Example usage
access_token = "56e085ab-387b-4696-8583-762fa32ab29b"
pubmed_id = "38365899"
download_pdf_with_selenium(pubmed_id, access_token, headless=True)
