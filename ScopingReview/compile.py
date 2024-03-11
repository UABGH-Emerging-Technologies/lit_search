import ScopingReview.generate as review_generate
import ScopingReview_config.config as review_config
from ScopingReview.data import write_excel_output
import pandas as pd
import streamlit as st
import tempfile


class CompileManager:
    def __init__(self, df):
        self.df = df
        
    def _download_results(self, articles_df, supplemental=''):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            write_excel_output(tmpfile, articles_df, supplemental)
            with open(tmpfile.name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=self.get_filename(),
                    mime="application/vnd.ms-excel"
                )
                
    def get_filename(self):
        # default implementation, subclasses can override this method
        return review_config.SR_STEP4_FILENAME
                    
class CategorizeManager(CompileManager):
    def __init__(self, df, userdefined_categories):
        super().__init__(df)
        self.userdefined_categories = userdefined_categories
        st.session_state['file_uploaded_cate'] = False  # Initiate a unique file_uploaded variable for categorization
    
    def get_filename(self):
        # default implementation, subclasses can override this method
        return review_config.SR_STEP3_FILENAME
                
    def categorize_articles(self):
        #uploaded_file = st.file_uploader("Upload file with Y/N filled in for categorizing", type=['xlsx'], key="uploader_cat")  # Add unique key
        if self.df is not None:
            st.session_state['file_uploaded_cate'] = True  # file is uploaded and ready to categorize
            with st.spinner("Categorizing contents of file..."):
                category_df = review_generate.categorize(self.df, self.userdefined_categories)
                self._download_results(category_df, self.userdefined_categories)


class SummarizeManager(CompileManager):
    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q
        st.session_state['file_uploaded_sum'] = False  # Initiate a unique file_uploaded variable for summarization

    def get_filename(self):
        return review_config.SR_STEP4_FILENAME
    
    def summarize_articles(self):
        if self.df is not None:
            st.session_state['file_uploaded_sum'] = True  # file is uploaded and ready to categorize
            with st.spinner("Summarizing categories of manuscripts..."):
                summary_df = review_generate.summarize_all_categories(self.df, self.research_q)
                self._download_results(summary_df)
                