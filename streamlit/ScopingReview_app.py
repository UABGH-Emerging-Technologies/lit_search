from datetime import datetime
from aiweb_common.streamlit.streamlit_common import apply_uab_font, hide_streamlit_branding
import streamlit as st
from ScopingReview.Bibliography.Manager import StreamlitBibtexManager
from ScopingReview.Categorize.Manager import FastAPICategorizeManager
from ScopingReview.Draft.Manager import DraftReviewManager
from ScopingReview.Summarize.Manager import SummarizeManager
from ScopingReview.Summarize.Workflow import SummarizeArticles
from ScopingReview.InitialSearch.Manager import StreamlitSearchManager  # <--- use this instead!
from ScopingReview.IterateSearch.Manager import FastAPIIterateSearchManager
from ScopingReview.Keywords.Manager import KeywordData
from aiweb_common.file_operations.upload_manager import StreamlitUploadManager
from states import (
    BibtexHandler,
    CategorizeHandler,
    DraftHandler,
    IterateHandler,
    SearchHandler,
    SummarizeHandler,
)


class LiteraturePage:
    def __init__(self):
        self.page_title = "Literature Search"
        self.page_icon = "📚"
        self.search_type_options = ["initial literature search", "work on scoping review"]
        self.query_type = None
        self.research_q = None
        self.scoping_step = None
        self.scoping_steps = [
            "first search",
            "iterate on search",
            "categorize articles",
            "summarize categories",
            "draft article",
            "generate bibtex file",
        ]

    def show(self):
        self._set_page_config()
        hide_streamlit_branding()
        apply_uab_font()
        self._show_page_content()
        prev_query_type = st.session_state.get("prev_query_type", None)
        self.query_type = st.radio(
            "Which of these best describes what you want help with?", self.search_type_options
        )
        if prev_query_type != self.query_type:
            st.session_state["button_clicked"] = False
            st.session_state["search_finished"] = False
            st.session_state["prev_query_type"] = self.query_type

        self.research_q = st.text_area(
            "Enter your research question/topic (or for a grant, your specific aims)",
            value=st.session_state.get("research_q", ""),
            placeholder="Enter your research question here and press Ctrl+Enter or click outside the text box to update.",
        )
        st.session_state["research_q"] = self.research_q

        # Reset button_clicked and search_finished if research question changes
        if "prev_research_q" not in st.session_state or st.session_state.prev_research_q != self.research_q:
            st.session_state["button_clicked"] = False
            st.session_state["search_finished"] = False
            st.session_state["prev_research_q"] = self.research_q

        if self.query_type == "work on scoping review":
            self.scoping_step = st.radio(
                "What step of the scoping review do you want to work on?", self.scoping_steps
            )

            # Reset button_clicked and search_finished if scoping step changes
            if "prev_scoping_step" not in st.session_state or st.session_state.prev_scoping_step != self.scoping_step:
                st.session_state["button_clicked"] = False
                st.session_state["search_finished"] = False
                st.session_state["prev_scoping_step"] = self.scoping_step

            self._manage_scoping_review()
        else:
            self._manage_initial_lit_review()

    def _set_page_config(self):
        st.set_page_config(page_title=self.page_title, page_icon=self.page_icon)

    def _show_page_content(self):
        st.title(f"{self.page_icon} {self.page_title} 🤖")
        st.markdown(
            """
        **Use generative AI to situate your research question in the context of existing literature.**

        Brought to you by the Anesthesiology Research Support, Informatics, and Data Science teams.

        _Not approved for use with PHI._

        All submissions are recorded for potential review by departmental and health system personnel.

        ---
        """
        )

    def _manage_scoping_review(self):
        if self.research_q == "":
            st.write("Please enter a research question to continue")
        else:
            if self.scoping_step in self.scoping_steps[:1]:
                self._manage_search()
            elif self.scoping_step == "iterate on search":
                self._manage_iterate_search()
            elif self.scoping_step == "categorize articles":
                self._manage_categorize_articles()
            elif self.scoping_step == "summarize categories":
                self._manage_summarize_categories()
            elif self.scoping_step == "draft article":
                self._manage_draft_article()
            elif self.scoping_step == "generate bibtex file":
                self._manage_bibtex()

    def _manage_search(self):
        smsearch = SearchHandler()
        smsearch.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            # USE STREAMLIT MANAGER HERE!
            st.session_state["search_manager"] = StreamlitSearchManager(
                None, self.research_q
            )
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            if st.button("Find Articles"):
                df = st.session_state["search_manager"].search_and_compile_articles()
                st.session_state["search_finished"] = True
                st.session_state["button_clicked"] = True
        if st.session_state["search_finished"]:
            smsearch.cleanup_states()

    def _manage_initial_lit_review(self):
        smsearch = SearchHandler()
        smsearch.initialize_states()
        smsummarize = SummarizeHandler()
        smsummarize.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            # USE STREAMLIT MANAGER HERE!
            st.session_state["search_manager"] = StreamlitSearchManager(
                None, self.research_q
            )
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            if st.button("Find Articles"):
                df = st.session_state["search_manager"].search_and_compile_articles(
                    write_excel=True
                )
                df = df.head(40)  # for now, GPT limitation
                df["Author 1: Relevant Article? (Yes/No)"] = "Yes"
                df["category"] = "Initial Search"
                df["Text"] = "Text not available"
                st.session_state["summarization_manager"] = SummarizeArticles(df, self.research_q)
                if "summarization_manager" in st.session_state:
                    st.session_state["summarization_finished"] = st.session_state[
                        "summarization_manager"
                    ].summarize_articles()
                    st.session_state["button_clicked"] = st.session_state["summarization_finished"]
                else:
                    st.write("Summarization manager not initialized yet.")
        if st.session_state["summarization_finished"]:
            smsearch.cleanup_states()
            smsummarize.cleanup_states()


    def _manage_iterate_search(self):
        smi = IterateHandler()
        smi.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            upload_manager = StreamlitUploadManager(st.file_uploader("Upload Excel File with Y/N selection", type=["xlsx"]))
            df, file_ext = upload_manager.process_upload()
            print("YOUR DF is - ", type(df))
            if df is not None:
                keywords = st.session_state.get("keywords_data")
                if keywords is None:
                    keywords = KeywordData(
                        primary_keywords=[],
                        secondary_keywords=[],
                        exclusion_keywords=[],
                    )
                st.session_state["search_manager"] = FastAPIIterateSearchManager(df, self.research_q, keywords)
                # initate keyword extraction right after file upload
                st.session_state["search_manager"].manage_keyword_extraction_and_editing()

            if isinstance(st.session_state["search_manager"], FastAPIIterateSearchManager):
                if (not st.session_state["button_clicked"]) and (
                    not st.session_state["search_finished"]
                ):
                    if st.session_state["keywords_finalized"]:
                        if st.button("Iterate Search"):
                            st.session_state["search_finished"] = st.session_state[
                                "search_manager"
                            ].search_and_compile_articles()
                            st.session_state["button_clicked"] = st.session_state["search_finished"]
                    else:
                        st.write("Please finalize keywords before continuing...")

        if st.session_state["search_finished"] and st.session_state["button_clicked"]:
            smi.cleanup_states()

    def _manage_edit_search_terms(self, search_manager):
        st.subheader("Edit Search Terms")
        search_manager.generate_and_refine_query()

    def _manage_categorize_articles(self):
        smc = CategorizeHandler()
        smc.initialize_states()
        start_time = datetime.now()
        if (not st.session_state["button_clicked"]) and (
            not st.session_state["categorization_finished"]
        ):
            upload_manager = StreamlitUploadManager(st.file_uploader("Upload Excel File with Y/N selection for Categorization", type=["xlsx"]))
            df, file_ext = upload_manager.process_upload()
            userdefined_categories = st.text_area(
                "Enter your list of categories, separated by commas:",
                "Category 1, Category 2, etc...",
            )

            if df is not None:
                if st.button("Categorize Topics"):
                    st.session_state["categorization_manager"] = FastAPICategorizeManager(
                        df, userdefined_categories
                    )
                    st.session_state["categorization_finished"] = st.session_state[
                        "categorization_manager"
                    ].categorize_articles_and_save()
                    st.session_state["button_clicked"] = st.session_state["categorization_finished"]

        if st.session_state["categorization_finished"]:
            smc.cleanup_states()

    def _manage_summarize_categories(self):
        import base64
        import json
        import requests
        smsummarize = SummarizeHandler()
        smsummarize.initialize_states()
        start_time = datetime.now()
        uploaded_file = st.file_uploader("Upload Excel file with Category labels to summarize", type=["xlsx"])
        if uploaded_file is not None:
            st.write("File uploaded:", uploaded_file.name)
            # Read file content and encode to base64
            file_bytes = uploaded_file.read()
            xlsx_encoded = base64.b64encode(file_bytes).decode("utf-8")
            # Prepare payload for API
            payload = {
                "research_question": self.research_q,
                "xlsx_encoded": xlsx_encoded,
            }
            if not st.session_state.get("button_clicked", False):
                if st.button("Summarize Categories"):
                    st.write("Summarize Categories button clicked")
                    with st.spinner("Summarizing articles"):
                        # Call backend step4 API
                        api_url = "http://localhost:8000/v01/scoping/step4/"
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
                        st.write(f"API response status: {response.status_code}")
                        if response.status_code == 200:
                            response_json = response.json()
                            encoded_docx = response_json.get("encoded_docx", None)
                            warning_msg = response.headers.get("Warning", "")
                            st.write(f"Encoded docx present: {encoded_docx is not None}")
                            if encoded_docx:
                                docx_bytes = base64.b64decode(encoded_docx)
                                st.session_state["summarization_manager"] = SummarizeManager(pd.DataFrame(), self.research_q)
                                st.session_state["summarization_finished"] = True
                                st.session_state["button_clicked"] = True
                                st.session_state["docx_bytes"] = docx_bytes
                                if warning_msg:
                                    st.warning(warning_msg)
                            else:
                                st.error("No summary document received from server.")
                        else:
                            st.error(f"Summarization failed: {response.status_code} {response.text}")

        if st.session_state.get("summarization_finished", False):
            smsummarize.cleanup_states()
            if "summarization_manager" in st.session_state and "docx_bytes" in st.session_state:
                st.write("Rendering download button")
                st.session_state["summarization_manager"].download_doc_results(st.session_state["docx_bytes"])

    def _manage_draft_article(self):
        smd = DraftHandler()
        smd.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["draft_complete"]:
            upload_manager = StreamlitUploadManager(st.file_uploader("Upload document of summaries to draft scoping review", type=["docx"]))
            summary_data, file_ext = upload_manager.process_upload()
            if st.button("Draft Review"):
                if summary_data is not None:
                    st.session_state["draft_manager"] = DraftReviewManager(
                        summary_data, self.research_q
                    )
                st.session_state["draft_complete"] = st.session_state[
                    "draft_manager"
                ].draft_review()
                st.session_state["button_clicked"] = st.session_state["draft_complete"]

        if st.session_state.get("draft_complete", False):
            smd.cleanup_states()
            draft_bytes = st.session_state.get("draft_result", None)
            if draft_bytes:
                st.success("Drafting completed successfully!")
                st.download_button(
                    label="Download Draft DOCX",
                    data=draft_bytes,
                    file_name="draft_review.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

    def _manage_bibtex(self):
        smb = BibtexHandler()
        smb.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["bibtex_complete"]:
            upload_manager = StreamlitUploadManager(st.file_uploader("Upload Finalized Excel sheet (CategorizeArticles.xlsx)", type=["xlsx", "docx"]))

            pmid_data, file_ext = upload_manager.process_upload()
            if st.button("Create Bibtex from File"):
                if pmid_data is not None:
                    st.session_state["bibtex_manager"] = StreamlitBibtexManager(pmid_data, file_ext)
                    st.session_state["bibtex_complete"] = st.session_state[
                        "bibtex_manager"
                    ].convert_pmid_to_bibtex()
                    st.session_state["button_clicked"] = st.session_state["bibtex_complete"]
                else:
                    st.write("Make sure input data is loaded")

        if st.session_state["bibtex_complete"]:
            smb.cleanup_states()


if __name__ == "__main__":
    literature_page = LiteraturePage()
    literature_page.show()
