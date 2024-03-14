import streamlit as st
import pandas as pd
import pypandoc
from ScopingReview.search import ArticleSearchManager, IterateSearchManager
from ScopingReview.compile import CategorizeManager, SummarizeManager, DraftReviewManager
import ScopingReview.generate as review_generate
from ScopingReview.data import write_excel_output
import tempfile
import ScopingReview_config.config as review_config



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
            self._manage_categorize_articles()
        elif self.scoping_step == "summarize categories":
            self._manage_summarize_categories()
        elif self.scoping_step == "draft article":
            self._manage_draft_article()
            
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
            st.session_state['button_clicked'] = False
            for key in st.session_state.keys():
                del st.session_state[key]
                
    def _manage_iterate_search(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
            st.session_state['search_finished'] = False

        if not st.session_state['button_clicked'] and not st.session_state['search_finished']:
            upload_manager = UploadManager(message="Upload Excel File with Y/N selection", 
                                        file_type = 'xlsx')
            df = upload_manager.upload_file()
            if df is not None:
                st.session_state['search_manager'] = IterateSearchManager(df)
                # This line is new and edits the search terms after uploading the dataframe
                self._manage_edit_search_terms(st.session_state['search_manager']) 

            if st.button("Iterate Search"):
                st.session_state['search_finished'] = st.session_state['search_manager'].search_and_compile_articles()
                st.session_state['button_clicked'] = st.session_state['search_finished']

        if st.session_state['search_finished']:
            for key in st.session_state.keys():
                del st.session_state[key]
                
    def _manage_edit_search_terms(self, search_manager):
        st.subheader("Edit Search Terms")
        search_manager.edit_query_terms()

    def _manage_categorize_articles(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
        if 'categorization_finished' not in st.session_state:
            st.session_state['categorization_finished'] = False

        if not st.session_state['button_clicked'] and not st.session_state['categorization_finished']:
            upload_manager = UploadManager(message = "Upload Excel File for Categorization", 
                                           file_type = 'xlsx')
            df = upload_manager.upload_file()
            userdefined_categories = st.text_area("Enter your list of categories, separated by commas:", "Category 1, Category 2, etc...")

            if st.button("Categorize Topics"):
                if df is not None:
                    st.session_state['categorization_manager'] = CategorizeManager(df, userdefined_categories)
                st.session_state['categorization_finished'] = st.session_state['categorization_manager'].categorize_articles()
                st.session_state['button_clicked'] = st.session_state['categorization_finished']

        if st.session_state['categorization_finished']:
            for key in st.session_state.keys():
                del st.session_state[key]

    def _manage_summarize_categories(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
        if 'summarization_finished' not in st.session_state:
            st.session_state['summarization_finished'] = False

        if not st.session_state['button_clicked'] and not st.session_state['summarization_finished']:
            upload_manager = UploadManager(message = "Upload Excel file with Category labels to summarize", 
                                        file_type = "xlsx")            
            df = upload_manager.upload_file()
            
            # checking the no. of articles in each category
            categories_exceeding_limit = []
            categories_exceeding_limit = review_generate.categories_limit_check(df)
            sub_categories = ""
            categories_str  = ""
                # TODO :   move this               
            def _download_results(category_df, updatedCategories):
                st.write("Note that once you hit download, this form will reset.")
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
                    write_excel_output(tmpfile, category_df, updatedCategories)
                    with open(tmpfile.name, "rb") as file:
                        st.balloons()
                        st.download_button(
                            label="Download Excel file",
                            data=file,
                            file_name="updatedCategories.xlsx",
                            mime=review_config.EXCEL_MIME
                        )
    
            # perfoming categorization on the exceeding limit categories
            if categories_exceeding_limit:
                categories_string = ", ".join(categories_exceeding_limit)
                sub_categories = st.text_area("More than 40 articles belong to the following category(ies). Suggest sub-categories for the following main category(ies), and separate them by commas:", categories_string)
                if st.button("Categorize Topics"):
                    df, categories_str = review_generate.sub_categorize(df, categories_exceeding_limit, sub_categories)
                    _download_results(df, ",".split(categories_str))
                    
                st.write("You must download and review the Excel file before continuing.")
                st.write("Refresh the page to summarize the articles.")
                            
            else:
                 # Summarizing
                if st.button("Summarize Categories"):
                    if df is not None:
                        st.session_state['summarization_finished'] = SummarizeManager(df, self.research_q)
                    st.session_state['summarization_finished'] = st.session_state['summarization_finished'].summarize_articles()
                    st.session_state['button_clicked'] = st.session_state['summarization_finished']
                    
                
                    
        if st.session_state['summarization_finished']:
            for key in st.session_state.keys():
                del st.session_state[key]
                
    def _manage_draft_article(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
        if 'draft_complete' not in st.session_state:
            st.session_state['draft_complete'] = False
            
        if not st.session_state['button_clicked'] and not st.session_state['draft_complete']:
            upload_manager = UploadManager(message = "Upload document of summaries to draft scoping review", 
                                        file_type = "docx")            
            summaries = upload_manager.upload_file()

            if st.button("Draft Review"):
                if summaries is not None:
                    st.session_state['draft_complete'] = DraftReviewManager(summaries, self.research_q)
                st.session_state['draft_complete'] = st.session_state['draft_complete'].draft_review()
                st.session_state['button_clicked'] = st.session_state['draft_complete']
                
        if st.session_state['draft_complete']:
            for key in st.session_state.keys():
                del st.session_state[key]
        
class UploadManager:
    def __init__(self, message:str, file_type:str):
        self.message = message
        self.file_type = file_type
        
    def upload_file(self):
        uploaded_file = st.file_uploader(self.message, type=[self.file_type])
        if self.file_type == 'xlsx':
            return pd.read_excel(uploaded_file) if uploaded_file is not None else None
        elif self.file_type == 'docx':
            if uploaded_file is not None:
            # Save the uploaded Word document to a temporary file
                with tempfile.NamedTemporaryFile(delete=True, suffix='.docx') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                    # Convert the temporary Word document to Markdown
                    converted = pypandoc.convert_file(tmp_path, 'markdown')
                    return converted
            else:
                return None
                    
                
if __name__ == "__main__":
    literature_page = LiteraturePage()
    literature_page.show()