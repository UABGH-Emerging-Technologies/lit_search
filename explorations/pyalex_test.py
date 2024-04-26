from io import BytesIO
from urllib.request import urlretrieve

import pdfplumber
import pyalex
import requests

pyalex.config.email = "rmelvin@uabmc.edu"
test = pyalex.Works()["https://doi.org/10.7717/peerj.4375"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3"
}


def extract_text_from_pdf_bytes(pdf_bytes):
    text = ""
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


if test["open_access"]:
    url = test["open_access"]["oa_url"]
    response = requests.get(url, allow_redirects=True, timeout=20, headers=headers)
    if response.ok and response.url.lower().endswith(".pdf"):
        text = extract_text_from_pdf_bytes(response.content)
