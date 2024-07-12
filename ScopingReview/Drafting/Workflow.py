from aiweb_common.WorkflowHandler import WorkflowHandler
import tempfile
from ScopingReview_config import config
from aiweb_common.generate import write_first_draft
from aiweb_common.file_operations.text_format import convert_markdown_docx

class DraftReview(WorkflowHandler):
    def __init__(self, summaries, research_q):
        super().__init__()
        self.summaries = summaries
        self.research_q = research_q

    def draft_review(self):
        if self.summaries is not None:
            markdown_to_convert, response_meta = write_first_draft(
                self.summaries, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            self._update_total_cost(response_meta)
            return docx_data

    def process(self):
        docx_data = self.draft_review()
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None
