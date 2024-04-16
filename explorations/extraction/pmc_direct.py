import requests
from Bio import Entrez

# Always tell NCBI who you are (your email address)
Entrez.email = "rmelvin@uab.edu"

import xml.etree.ElementTree as ET

from Bio import Entrez


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


def get_pdf_url(pmcid):
    url = f"http://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmcid}&blobtype=pdf"
    response = requests.get(url, allow_redirects=True)
    final_url = response.url
    return final_url


# Example usage
pmid = "24958300"
pmcid = get_pmcid_from_pubmed(pmid)
if pmcid:
    pdf_url = get_pdf_url(pmcid)
    if pdf_url:
        print(f"PDF URL for PMCID {pmcid} is: {pdf_url}")
    else:
        print(f"Could not retrieve PDF for PMCID {pmcid}")
else:
    print(f"No PMCID found for PMID {pmid}")
