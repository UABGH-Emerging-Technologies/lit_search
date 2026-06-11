import tempfile

from aiweb_common.file_operations.text_format import convert_markdown_docx

import streamlit as st
from ScopingReview.BaseManager import BaseManager
from ScopingReview_config import config


class DraftReviewManager(BaseManager):
    """Manages the assembly of a scoping-review draft from category summaries.

    Args:
        summaries: Markdown string of all category summaries.
        research_q: The research question.
    """

    def __init__(self, summaries, research_q):
        super().__init__(None)  # Assuming the base class does not necessarily need a DataFrame
        self.research_q = research_q
        self.summaries = summaries

    def get_filename(self) -> str:
        return config.SR_STEP5_FILENAME

    def get_mime_type(self) -> str:
        return config.DOCX_MIME

    # TODO: find better place for this. Used by write_first_draft()
    @staticmethod
    def extract_apa_citations(markdown_text):
        """Separate APA citation paragraphs from body paragraphs in markdown text.

        Args:
            markdown_text: Full markdown text with embedded PMID citations.

        Returns:
            Tuple of (citation_paragraphs, non_citation_paragraphs).
        """
        # Split the document into paragraphs
        paragraphs = markdown_text.split("\n\n")

        # Filter paragraphs that contain "PMID"
        citations = [para for para in paragraphs if "PMID" in para]
        non_citations = [para for para in paragraphs if "PMID" not in para]

        return citations, non_citations

    @staticmethod
    def assemble_document(
        abstract_md, intro_md, methods_md, results_md, conclusion_md, citations_md
    ):
        """Assemble the complete draft document from individual section strings.

        Args:
            abstract_md: Abstract section markdown.
            intro_md: Introduction section markdown.
            methods_md: Methodology section markdown.
            results_md: List of results/discussion section paragraphs.
            conclusion_md: Conclusion section markdown.
            citations_md: List of citation paragraphs.

        Returns:
            Assembled markdown string of the full draft.
        """
        assembled_draft = (
            abstract_md
            + "\n\n"
            + intro_md
            + "\n\n"
            + methods_md
            + "\n\n"
            + "# Results/Discussion \n\n"
            + "\n\n".join(results_md)
            + "\n\n"
            + conclusion_md
            + "\n\n"
            + "# References \n\n"
            + "\n\n".join(citations_md)
        )

        return assembled_draft


class StreamlitDraftReviewManager(DraftReviewManager):
    """Streamlit UI wrapper for draft review with download buttons."""

    def __init__(self, summaries, research_q):
        super().__init__(summaries, research_q)
        st.session_state["file_uploaded_draft"] = (
            False  # Unique file_uploaded variable for drafting
        )

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
