import tempfile

import pandas as pd
from aiweb_common.WorkflowHandler import WorkflowHandler

from ScopingReview.Bibliography.Manager import FastAPIBibtexManager
from ScopingReview_config import config


class BibtexWorkflow(WorkflowHandler):
    """Orchestrates PMID-to-BibTeX conversion and writes output to a temp file.

    Args:
        file_contents: DataFrame or text string containing PMIDs.
        file_ext: Source file extension (``".xlsx"`` or ``".docx"``).
    """

    def __init__(self, file_contents, file_ext):
        super().__init__()
        self.bib_manager = FastAPIBibtexManager(file_contents, file_ext)

    def get_filename(self):
        """Return the configured BibTeX output filename."""
        return config.SR_STEP6_FILENAME

    def process(self):
        """Convert PMIDs to BibTeX and write to a temporary file.

        Returns:
            Path to the temporary ``.bib`` file, or ``None`` on failure.
        """
        bibtex_text = self.bib_manager.convert_pmid_to_bibtex()
        if bibtex_text:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".bib", mode="w", encoding="utf-8"
            ) as tmpfile:
                tmpfile.write(bibtex_text)
                return tmpfile.name
        return None
