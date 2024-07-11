from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config
from ScopingReview.SearchWorkflow import extract_docx_pmids
from ScopingReview.utils import pmid2bibtex

class BibtexManager(WorkflowHandler):
    def __init__(self, file_contents, file_ext):
        super().__init__()
        self.file_contents = file_contents
        self.file_ext = file_ext
        if file_contents is not None:
            self.df = file_contents

    def _get_PMID_list(self):
        if self.file_ext == ".xlsx":
            if "PMID" in self.df.columns:
                return self.df["PMID"].astype(str).tolist()
            else:
                raise ValueError("PMIDs missing.")
        elif self.file_ext == ".docx":
            df = extract_docx_pmids(self.df)
            if "PMID" in df.columns:
                return df["PMID"].astype(str).tolist()
            else:
                raise ValueError("Bibliography not in expected format.")

    def convert_pmid_to_bibtex(self):
        pmid_list = self._get_PMID_list()
        if not pmid_list:
            raise ValueError("No PMIDs found to convert to BibTeX.")
        bibtex_text = pmid2bibtex(pmid_list)
        return bibtex_text

    def process(self):
        bibtex_text = self.convert_pmid_to_bibtex()
        if bibtex_text:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bib", mode='w', encoding='utf-8') as tmpfile:
                tmpfile.write(bibtex_text)
                return tmpfile.name
        return None
