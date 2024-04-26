from Bio import Entrez, Medline

Entrez.email = "rmelvin@uabmc.edu"
handle = Entrez.efetch(db="pubmed", id="32076685", rettype="medline", retmode="text")
articles = Medline.parse(handle)
article = list(articles)[0]
handle.close()
article
