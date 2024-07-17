from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config
from ScopingReview.Bibliography.Manager import FastAPIBibtexManager

# The `BibtexWorkflow` class handles the conversion of a PMID to BibTeX format and writes it to a
# temporary file.
class BibtexWorkflow(WorkflowHandler):
    def __init__(self, file_contents, file_ext):
        super().__init__()
        self.bib_manager = FastAPIBibtexManager(file_contents, file_ext)

    def get_filename(self):
        return config.SR_STEP6_FILENAME

    def process(self):
        """
        The `process` function converts a PMID to BibTeX format and writes it to a temporary file, returning
        the file name.
        
        Returns:
          The `process` method returns the name of a temporary file that is created and written with the
        BibTeX text converted from a PMID using the `convert_pmid_to_bibtex` method of the `bib_manager`. If
        the BibTeX text is successfully retrieved and written to the temporary file, the method returns the
        name of the temporary file. If there is no BibTeX text retrieved, it returns
        """
        bibtex_text = self.bib_manager.convert_pmid_to_bibtex()
        if bibtex_text:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bib", mode='w', encoding='utf-8') as tmpfile:
                tmpfile.write(bibtex_text)
                return tmpfile.name
        return None
