import streamlit as st
import pandas as pd
from ScopingReview.search import ArticleSearchManager, IterateSearchManager
from ScopingReview.compile import CategorizeManager, SummarizeManager

from llm_utils.streamlit_common import hide_streamlit_branding, apply_uab_font

class LiteraturePage:
    def __init__(self):
        self.page_title = "Literature Search"
        self.page_icon = "📚"
        self.search_type_options = [
            "assess the novelty of my idea",
            "get a jump start on my literature search",
            "estimate the complexity and feasibility of my idea",
            "identify weaknesses or gaps in the literature that serve as the key support for a proposed NIH-style grant",
            "work on scoping review"
        ]
        self.query_type = None
        self.research_q = None
        self.scoping_step = None
        self.scoping_steps = [
            "first search",
            "iterate on search",
            "categorize articles",
            "summarize categories",
            "draft article"
        ]

    def show(self):
        self._set_page_config()
        hide_streamlit_branding()
        apply_uab_font()
        self._show_page_content()
        self.query_type = st.radio("Which of these best describes what you want help with?", self.search_type_options)
        self.research_q = st.text_area("Enter your research question/topic (or for a grant, your specific aims)",
                                "Does a diagnosis of a connective tissue disease contribute to a post-dural spinal puncture headache?")
        if self.query_type == "work on scoping review":
            self.scoping_step = st.radio("What step of the scoping review do you want to work on?", self.scoping_steps)
            self._manage_scoping_review()
        else:
            self._manage_search()

    def _set_page_config(self):
        st.set_page_config(page_title=self.page_title, page_icon=self.page_icon)

    def _show_page_content(self):
        st.title(f"{self.page_icon} {self.page_title} 🤖")
        st.markdown("""
        **Use generative AI to situate your research question in the context of existing literature.**

        Brought to you by the Anesthesiology Research Support, Informatics, and Data Science teams.

        _Not approved for use with PHI._

        All submissions are recorded for potential review by departmental and health system personnel.

        ---
        """)

    def _manage_scoping_review(self):
        if self.scoping_step in self.scoping_steps[:1]:
            self._manage_search()
        elif self.scoping_step == "iterate on search":
            self._manage_iterate_search()
        elif self.scoping_step == "categorize articles":
            self._categorize_articles()
        elif self.scoping_step == "summarize categories":
            self._summarize_categories()

    def _manage_iterate_search(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
            st.session_state['search_finished'] = False

        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            upload_manager = UploadManager()
            df = upload_manager.upload_file()
            if st.button("Iterate Search"):
                if df is not None:
                    st.session_state['search_manager'] = IterateSearchManager(df)
                st.session_state['search_finished'] = st.session_state['search_manager'].search_and_compile_articles()
                st.session_state['button_clicked'] = st.session_state['search_finished']

        if st.session_state['search_finished']:
            for key in st.session_state.keys():
                del st.session_state[key]

    def _manage_search(self):
        # Check if 'button_clicked' is already a key in session_state
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
            st.session_state['search_finished'] = False
            st.session_state['search_manager'] = ArticleSearchManager(self.scoping_step, self.research_q)

        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            if st.button("Find Articles"):
                st.session_state['search_finished'] = st.session_state['search_manager'].search_and_compile_articles()
                st.session_state['button_clicked'] = st.session_state['search_finished']

        if st.session_state['search_finished']:
            #st.session_state['button_clicked'] = False
            for key in st.session_state.keys():
                del st.session_state[key]

    def _iterate_search(self):
        upload_manager = UploadManager()
        df = upload_manager.upload_file()
        if df is not None:
            iterate_search_manager = IterateSearchManager(df)
            iterate_search_manager.search_and_compile_articles()

    def _categorize_articles(self):
        upload_manager = UploadManager()
        df = upload_manager.upload_file()
        input_text = st.text_area("Enter your list of categories, separated by commas:", "Category 1, Category 2, etc...")

        if st.button("Categorize Topics"):
            if df is not None:
                categorize_manager = CategorizeManager(df, self.research_q)
                categorize_manager.categorize_articles(input_text)

    def _summarize_categories(self):
        upload_manager = UploadManager()
        df = upload_manager.upload_file()
        if st.button("Summarize Categories"):
            if df is not None:
                summary_manager = SummarizeManager(df, self.research_q)
                summary_manager.summarize_articles()
        
class UploadManager:
    def upload_file(self):
        uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])
        return pd.read_excel(uploaded_file) if uploaded_file is not None else None


if __name__ == "__main__":
    literature_page = LiteraturePage()
    literature_page.show()