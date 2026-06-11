# Bibliography (BibTeX)

Converts PubMed article identifiers to BibTeX format. Accepts either an Excel
file with a PMID column or a DOCX file containing PMIDs, fetches citation
metadata from NCBI Entrez, and formats it as a `.bib` file.

**Input:** Excel or DOCX file with PMIDs

**Output:** BibTeX file (base64-encoded `.bib`)

## Manager

::: ScopingReview.Bibliography.Manager
    options:
      members:
        - BibliographyManager
        - FastAPIBibtexManager

## Workflow

::: ScopingReview.Bibliography.Workflow
