from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config
from ScopingReview.Bibliography.Manager import FastAPIBibtexManager

class BibtexWorkflow(WorkflowHandler):
    def __init__(self, file_contents, file_ext):
        super().__init__()
        self.bib_manager = FastAPIBibtexManager(file_contents, file_ext)

    def get_filename(self):
        return config.SR_STEP6_FILENAME

    def process(self):
        bibtex_text = self.bib_manager.convert_pmid_to_bibtex()
        if bibtex_text:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bib", mode='w', encoding='utf-8') as tmpfile:
                tmpfile.write(bibtex_text)
                return tmpfile.name
        return None
