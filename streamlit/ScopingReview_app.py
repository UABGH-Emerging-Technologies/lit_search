from llm_utils.streamlit_common import apply_uab_font, hide_streamlit_branding
import streamlit as st
from ScopingReview.compile import (
    BibtexManager,
    CategorizeManager,
    DraftReviewManager,
    SummarizeManager,
)
from ScopingReview.search import ArticleSearchManager, IterateSearchManager
from ScopingReview.states import (
    BibtexHandler,
    CategorizeHandler,
    DraftHandler,
    IterateHandler,
    SearchHandler,
    SummarizeHandler,
)
from ScopingReview.data import write_to_db
from ScopingReview.upload import UploadManager
from datetime import datetime


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
        self.query_type = st.radio(
            "Which of these best describes what you want help with?", self.search_type_options
        )
        self.research_q = st.text_area(
            "Enter your research question/topic (or for a grant, your specific aims)",
            value="",
            placeholder="Enter your research question here and press Ctrl+Enter or click outside the text box to update.",
        )
        if self.query_type == "work on scoping review":
            self.scoping_step = st.radio(
                "What step of the scoping review do you want to work on?", self.scoping_steps
            )
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
        # Check if 'button_clicked' is already a key in session_state
        smsearch = SearchHandler()
        smsearch.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            st.session_state["search_manager"] = ArticleSearchManager(
                self.scoping_step, self.research_q
            )

        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            if st.button("Find Articles"):
                st.session_state["search_finished"] = st.session_state[
                    "search_manager"
                ].search_and_compile_articles()
                # for non-scoping, then summarize and download
                st.session_state["button_clicked"] = st.session_state["search_finished"]

        if st.session_state["search_finished"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smsearch.cleanup_states()

    def _manage_initial_lit_review(self):
        smsearch = SearchHandler()
        smsearch.initialize_states()
        smsummarize = SummarizeHandler()
        smsummarize.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            st.session_state["search_manager"] = ArticleSearchManager(
                self.scoping_step, self.research_q
            )

        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            if st.button("Find Articles"):
                df = st.session_state["search_manager"].search_and_compile_articles(
                    write_excel=False
                )
                df = df.head(40)  # for now, GPT limitation
                df["Author 1: Relevant Article? (Yes/No)"] = "Yes"
                df["category"] = "Initial Search"
                df["Text"] = "Text not available"
                # for non-scoping, then summarize and download
                st.session_state["summarization_manager"] = SummarizeManager(df, self.research_q)
                st.session_state["summarization_finished"] = st.session_state[
                    "summarization_manager"
                ].summarize_articles()
                st.session_state["button_clicked"] = st.session_state["summarization_finished"]

        if st.session_state["summarization_finished"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smsearch.cleanup_states()
            smsummarize.cleanup_states()

    def _manage_iterate_search(self):
        smi = IterateHandler()
        smi.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["search_finished"]:
            upload_manager = UploadManager(
                message="Upload Excel File with Y/N selection", file_types=["xlsx"]
            )
            df, file_ext = upload_manager.upload_file()
            print("YOUR DF is - ", type(df))
            if df is not None:
                st.session_state["search_manager"] = IterateSearchManager(df, self.research_q)
                # initate keyword extraction right after file upload
                st.session_state["search_manager"].manage_keyword_extraction_and_editing()

            if isinstance(st.session_state["search_manager"], IterateSearchManager):
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
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
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
            upload_manager = UploadManager(
                message="Upload Excel File with Y/N selection for Categorization",
                file_types=["xlsx"],
            )
            df, file_ext = upload_manager.upload_file()
            userdefined_categories = st.text_area(
                "Enter your list of categories, separated by commas:",
                "Category 1, Category 2, etc...",
            )

            if df is not None:
                if st.button("Categorize Topics"):
                    st.session_state["categorization_manager"] = CategorizeManager(
                        df, userdefined_categories
                    )
                    st.session_state["categorization_finished"] = st.session_state[
                        "categorization_manager"
                    ].categorize_articles()
                    st.session_state["button_clicked"] = st.session_state["categorization_finished"]

        if st.session_state["categorization_finished"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smc.cleanup_states()

    def _manage_summarize_categories(self):
        smsummarize = SummarizeHandler()
        smsummarize.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"]:
            upload_manager = UploadManager(
                message="Upload Excel file with Category labels to summarize", file_types=["xlsx"]
            )
            df, file_ext = upload_manager.upload_file()
            if df is not None:
                st.session_state["summarization_manager"] = SummarizeManager(df, self.research_q)
                # checking the no. of articles in each category and subcategorizing as needed.
                st.session_state["summarization_manager"].subcategorize()

                if st.session_state["subcategorize_complete"] and (
                    not st.session_state["limit_exceeded"]
                ):
                    # Summarizing
                    if st.button("Summarize Categories"):
                        st.spinner("Summarizing articles")
                        st.session_state["summarization_finished"] = st.session_state[
                            "summarization_manager"
                        ].summarize_articles()
                        st.session_state["button_clicked"] = st.session_state[
                            "summarization_finished"
                        ]

        if st.session_state["summarization_finished"] or st.session_state["subcategorize_complete"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smsummarize.cleanup_states()

    def _manage_draft_article(self):
        smd = DraftHandler()
        smd.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["draft_complete"]:
            upload_manager = UploadManager(
                message="Upload document of summaries to draft scoping review", file_types=["docx"]
            )
            summary_data, file_ext = upload_manager.upload_file()
            if st.button("Draft Review"):
                if summary_data is not None:
                    st.session_state["draft_manager"] = DraftReviewManager(
                        summary_data, self.research_q
                    )
                st.session_state["draft_complete"] = st.session_state[
                    "draft_manager"
                ].draft_review()
                st.session_state["button_clicked"] = st.session_state["draft_complete"]

        if st.session_state["draft_complete"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smd.cleanup_states()

    def _manage_bibtex(self):
        smb = BibtexHandler()
        smb.initialize_states()
        start_time = datetime.now()
        if not st.session_state["button_clicked"] and not st.session_state["bibtex_complete"]:
            upload_manager = UploadManager(
                message="Upload Finalized Excel sheet (CategorizeArticles.xlsx)",
                file_types=["xlsx", "docx"],
            )

            pmid_data, file_ext = upload_manager.upload_file()
            if st.button("Create Bibtex from File"):
                if pmid_data is not None:
                    st.session_state["bibtex_manager"] = BibtexManager(pmid_data, file_ext)
                    st.session_state["bibtex_complete"] = st.session_state[
                        "bibtex_manager"
                    ].convert_pmid_to_bibtex()
                    st.session_state["button_clicked"] = st.session_state["bibtex_complete"]
                else:
                    st.write("Make sure input data is loaded")

        if st.session_state["bibtex_complete"]:
            write_to_db(
                self.research_q,
                self.query_type,
                start_time,
                datetime.now(),
                st.session_state["total_cost"],
            )
            smb.cleanup_states()


if __name__ == "__main__":
    literature_page = LiteraturePage()
    literature_page.show()
