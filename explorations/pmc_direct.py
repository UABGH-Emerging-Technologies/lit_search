import requests
from Bio import Entrez

# Always tell NCBI who you are (your email address)
Entrez.email = "rmelvin@uab.edu"

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
    response = requests.get(url, allow_redirects=True)
    final_url = response.url
    return(final_url)

# Example usage
pmid = "38365899"
pmcid = get_pmcid_from_pubmed(pmid)
if pmcid:
    pdf_url = get_pdf_url(pmcid)
    if pdf_url:
        print(f"PDF URL for PMCID {pmcid} is: {pdf_url}")
    else:
        print(f"Could not retrieve PDF for PMCID {pmcid}")
else:
    print(f"No PMCID found for PMID {pmid}")