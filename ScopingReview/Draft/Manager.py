from ScopingReview_config import config
from ScopingReview.BaseManager import BaseManager
from aiweb_common.file_operations.text_format import convert_markdown_docx
import streamlit as st
import tempfile

class DraftReviewManager(BaseManager):
    def __init__(self, summaries, research_q):
        super().__init__(None)  # Assuming the base class does not necessarily need a DataFrame
        self.research_q = research_q
        self.summaries = summaries

    def get_filename(self) -> str:
        return config.SR_STEP5_FILENAME

    def get_mime_type(self) -> str:
        return config.DOCX_MIME

    def draft_review(self) -> bytes:
        """
        Generates a first draft of the document based on summaries and a research question.
        Returns the binary data of the DOCX file.
        """
        #TODO Plugin the aiweb_common and move to workflow!
        if self.summaries is not None:
            markdown_to_convert = self.write_first_draft(
                self.summaries, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            return docx_data
        else:
            raise ValueError("Summaries data is required for drafting.")

    def save_draft_review(self, docx_data: bytes) -> str:
        """
        Saves the generated draft review to a DOCX file and returns the file path.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        except Exception as e:
            raise IOError(f"Failed to save draft review document: {str(e)}")
        
    # TODO: find better place for this. Used by write_first_draft()
    def extract_apa_citations(markdown_text):
        # Split the document into paragraphs
        paragraphs = markdown_text.split("\n\n")

        # Filter paragraphs that contain "PMID"
        citations = [para for para in paragraphs if "PMID" in para]
        non_citations = [para for para in paragraphs if "PMID" not in para]

        return citations, non_citations




class StreamlitDraftReviewManager(DraftReviewManager):
    def __init__(self, summaries, research_q):
        super().__init__(summaries, research_q)
        st.session_state["file_uploaded_draft"] = False  # Unique file_uploaded variable for drafting

    def _download_results(self, docx_data):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_filename(),
            mime=self.get_mime_type(),
        )

    def draft_review(self):
        docx_data = super().draft_review()
        if docx_data:
            self._download_results(docx_data)
            st.session_state["file_uploaded_draft"] = True


class FastAPIDraftReviewManager(DraftReviewManager):
    def __init__(self, summaries, research_q):
        super().__init__(summaries, research_q)

    def draft_review(self) -> bytes:
        """
        Asynchronously generate a first draft of the document based on summaries and a research question.
        Returns the binary data of the DOCX file.
        Overrides the base method to include proper error handling in an asynchronous context.
        """
        if not self.summaries:
            raise HTTPException(status_code=400, detail="Summaries data is required for drafting.")
        
        try:
            markdown_to_convert, response_meta = lit_generate.write_first_draft(
                self.summaries, self.research_q
            )
            self.cost += response_meta.total_cost
            docx_data = convert_markdown_docx(markdown_to_convert)
            return docx_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate draft: {str(e)}")

    def save_draft_review(self, docx_data: bytes) -> str:
        """
        Asynchronously save the generated draft review to a DOCX file and return the file path.
        """
        try:
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, self.get_filename())
            with open(file_path, "wb") as file:
                file.write(docx_data)
            return file_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save draft review document: {str(e)}")
