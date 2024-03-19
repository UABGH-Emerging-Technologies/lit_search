import streamlit as st
import pandas as pd
from ScopingReview.compile import CategorizeManager, SummarizeManager, DraftReviewManager
from ScopingReview.search import ArticleSearchManager, IterateSearchManager
import ScopingReview.generate as review_generate
from ScopingReview.data import write_excel_output
import tempfile
import ScopingReview_config.config as review_config
from ScopingReview.states import StateMachineSearch, StateMachineIterate, StateMachineSummarize, StateMachineCategorize, StateMachineDraft


from llm_utils.streamlit_common import hide_streamlit_branding, apply_uab_font

class LiteraturePage:
    def __init__(self):
        self.page_title = "Literature Search"
        self.page_icon = "📚"
        self.search_type_options = [
            "initial literature search",
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
            self._manage_initial_lit_review()

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
            self._manage_categorize_articles()
        elif self.scoping_step == "summarize categories":
            self._manage_summarize_categories()
        elif self.scoping_step == "draft article":
            self._manage_draft_article()
            
    def _manage_search(self):
        # Check if 'button_clicked' is already a key in session_state
        smsearch = StateMachineSearch()
        smsearch.initialize_states()
        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:

            st.session_state['search_manager'] = ArticleSearchManager(self.scoping_step, self.research_q)

        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            if st.button("Find Articles"):
                st.session_state['search_finished'] = st.session_state['search_manager'].search_and_compile_articles()
                # for non-scoping, then summarize and download
                st.session_state['button_clicked'] = st.session_state['search_finished']

        if st.session_state['search_finished']:
            smsearch.cleanup_states()
            
    def _manage_initial_lit_review(self):
        # Check if 'button_clicked' is already a key in session_state
        smsearch = StateMachineSearch()
        smsearch.initialize_states()
        smsummarize = StateMachineSummarize()
        smsummarize.initialize_states()
        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:

            st.session_state['search_manager'] = ArticleSearchManager(self.scoping_step, self.research_q)

        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            if st.button("Find Articles"):
                df = st.session_state['search_manager'].search_and_compile_articles(write_excel=False)
                df = df.head(40) # for now, GPT limitation
                df['Author 1: Relevant Article? (Yes/No)'] = "Yes"
                df['category'] = "Initial Search"
                df['Text'] = "Text not available"
                # for non-scoping, then summarize and download
                st.session_state['summarization_manager'] = SummarizeManager(df, self.research_q)
                st.session_state['summarization_finished'] = st.session_state['summarization_manager'].summarize_articles()
                st.session_state['button_clicked'] = st.session_state['summarization_finished']

        if st.session_state['summarization_finished']:
            smsearch.cleanup_states()
            smsummarize.cleanup_states()
                
            
    def _manage_iterate_search(self):       
        smi = StateMachineIterate()
        smi.initialize_states()
        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            upload_manager = UploadManager(message="Upload Excel File with Y/N selection", 
                                        file_type = 'xlsx')
            df = upload_manager.upload_file()
            if df is not None:
                st.session_state['search_manager'] = IterateSearchManager(df, self.research_q)
                # initate keyword extraction right after file upload
                st.session_state['search_manager'].manage_keyword_extraction_and_editing()

            if isinstance(st.session_state['search_manager'], IterateSearchManager):
                if (not st.session_state['button_clicked']) and (not st.session_state['search_finished']):

                    if st.button("Iterate Search"):
                        if st.session_state["keywords_finalized"]:
                            st.session_state['search_finished'] = st.session_state['search_manager'].search_and_compile_articles()
                            st.session_state['button_clicked'] = st.session_state['search_finished']
                        else:
                            st.write("Please finalize keywords before continuing...")
                            
        if st.session_state['search_finished'] and st.session_state['button_clicked']:
            smi.cleanup_states()
                
    def _manage_edit_search_terms(self, search_manager):
        st.subheader("Edit Search Terms")
        search_manager.generate_and_refine_query()

    def _manage_categorize_articles(self):
        smc = StateMachineCategorize()
        smc.initialize_states()
        if (not st.session_state['button_clicked']) and (not st.session_state['categorization_finished']):
            upload_manager = UploadManager(message = "Upload Excel File for Categorization", 
                                           file_type = 'xlsx')
            df = upload_manager.upload_file()
            userdefined_categories = st.text_area("Enter your list of categories, separated by commas:", "Category 1, Category 2, etc...")

            if df is not None:
                if st.button("Categorize Topics"):
                    st.session_state['categorization_manager'] = CategorizeManager(df, userdefined_categories)
                    st.session_state['categorization_finished'] = st.session_state['categorization_manager'].categorize_articles()
                    st.session_state['button_clicked'] = st.session_state['categorization_finished']

        if st.session_state['categorization_finished']:
            smc.cleanup_states()
    
    def _manage_summarize_categories(self):
        smsummarize = StateMachineSummarize()
        smsummarize.initialize_states()
        if not st.session_state['button_clicked'] and not st.session_state['summarization_finished']:
            upload_manager = UploadManager(message = "Upload Excel file with Category labels to summarize", 
                                        file_type = "xlsx")            
            df = upload_manager.upload_file()
            if df is not None:
                st.session_state['summarization_manager'] = SummarizeManager(df, self.research_q)
                # checking the no. of articles in each category and subcategorizing as needed.
                st.session_state['summarization_manager'].subcategorize()         
                     
            # Summarizing
            if st.button("Summarize Categories"):
                if st.session_state['subcategorize_complete']:
                    st.spinner("Summarizing articles")
                    st.session_state['summarization_finished'] = st.session_state['summarization_manager'].summarize_articles()
                    st.session_state['button_clicked'] = st.session_state['summarization_finished']
                else: 
                    st.write("Please execute subcategorization first")
                
        if st.session_state['summarization_finished']:
            smsummarize.cleanup_states()
                
    def _manage_draft_article(self):
        smd = StateMachineDraft()
        smd.initialize_states()
        if not st.session_state['button_clicked'] and not st.session_state['draft_complete']:
            upload_manager = UploadManager(message = "Upload document of summaries to draft scoping review", 
                                        file_type = "docx")            
            summary_data = upload_manager.upload_file()
            print("SUMMARY UPLOADED - ", summary_data)
            if st.button("Draft Review"):
                if summary_data is not None:
                    st.session_state['draft_manager'] = DraftReviewManager(summary_data, self.research_q)
                st.session_state['draft_complete'] = st.session_state['draft_manager'].draft_review()
                st.session_state['button_clicked'] = st.session_state['draft_complete']
                
        if st.session_state['draft_complete']:
            smd.cleanup_states()
        
class UploadManager:
    def __init__(self, message:str, file_type:str):
        self.message = message
        self.file_type = file_type
        
    def upload_file(self):
        uploaded_file = st.file_uploader(self.message, type=[self.file_type])
        if self.file_type == 'xlsx':
            return pd.read_excel(uploaded_file) if uploaded_file is not None else None
        elif self.file_type == 'docx':
            #TODO -update this part for step 5
            pass
            
if __name__ == "__main__":
    literature_page = LiteraturePage()
    literature_page.show()