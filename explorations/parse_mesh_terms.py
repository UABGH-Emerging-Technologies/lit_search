from Bio import Entrez, Medline
Entrez.email = "rmelvin@uabmc.edu"
handle = Entrez.efetch(db="pubmed", id="38381674", retmode="xml")
articles = Entrez.read(handle)["PubmedArticle"]
handle.close()
article = articles[0]

from llm_utils import text_format


key_words = text_format.extract_mesh_elements(article['MedlineCitation']['MeshHeadingList'])