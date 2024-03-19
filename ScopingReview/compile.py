import ScopingReview.generate as review_generate
import ScopingReview_config.config as review_config
from ScopingReview.data import write_excel_output, fetch_full_text
from llm_utils.text_format import convert_markdown_docx
import pandas as pd
import streamlit as st
import tempfile


class CompileManager:
    def __init__(self, df):
        self.df = df
                
    def get_filename(self):
        # default implementation, subclasses MUST override this method
        pass
    
    def get_mime_type(self):
        # default implementation, subclasses MUST override this method
        pass     
                  
class CategorizeManager(CompileManager):
    def __init__(self, df, userdefined_categories):
        super().__init__(df)
        self.userdefined_categories = userdefined_categories
        st.session_state['file_uploaded_cate'] = False  # Initiate a unique file_uploaded variable for categorization
                
    def get_mime_type(self):
        return review_config.EXCEL_MIME
            
    def get_filename(self):
        # default implementation, subclasses can override this method
        return review_config.SR_STEP3_FILENAME
    
    def get_download_button_label(self):
        return review_config.EXCEL_DOWNLOAD_LABEL
                        
    def categorize_articles(self):
        if self.df is not None:
            st.session_state['file_uploaded_cate'] = True  # file is uploaded and ready to categorize
            with st.spinner("Categorizing contents of file..."):
                category_df = review_generate.categorize(self.df, self.userdefined_categories)
                
            with st.spinner("Getting full text"):
                full_text_df = fetch_full_text(category_df.PMID)
                category_df = pd.merge(category_df, full_text_df, on="PMID", how="inner")
                
            self._download_results(category_df)
    
    def _download_results(self, category_df):
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            write_excel_output(tmpfile, category_df, self.userdefined_categories)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_filename(),
                    mime=self.get_mime_type()
                )      


class SummarizeManager(CompileManager):
    def __init__(self, df, research_q):
        super().__init__(df)

        self.research_q = research_q
        self.categories = []
        self.sub_categories = ""
        self.categories_str  = ""
        st.session_state['file_uploaded_sum'] = False  # Initiate a unique file_uploaded variable for summarization

    def get_doc_filename(self):
        return review_config.SR_STEP4_DOCX_FILENAME
    def get_excel_filename(self):
        return review_config.SR_STEP4_EXCEL_FILENAME
    def get_download_button_label(self):
        return review_config.BOTH_FILES
    
    #TODO add write and second sheet + Generalize and move to parent
    def _download_excel_results(self, categories_str):
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
            write_excel_output(tmpfile, self.df, categories_str)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_excel_filename(),
                    mime=review_config.EXCEL_MIME
                )      
                
    def _download_doc_results(self, docx_data):
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_doc_filename(),
            mime=review_config.DOCX_MIME  # correct MIME type for docx
        )   
            
    def check_limits(self):
        categories_exceeding_limit = review_generate.categories_limit_check(self.df)
        return categories_exceeding_limit
    
    def subcategorize(self):
        categories_exceeding_limit = self.check_limits()
        # perfoming categorization on the exceeding limit categories
        if categories_exceeding_limit:
            categories_string = ", ".join(categories_exceeding_limit)
            sub_categories = st.text_area("More than 40 articles belong to the following category(ies). Suggest sub-categories for the following main category(ies), and separate them by commas:", categories_string)
            if st.button("Subcategorize Topics"):
                self.df, self.categories_str = review_generate.sub_categorize(self.df, categories_exceeding_limit, sub_categories)
                st.session_state['subcategorize_complete'] = True
                self._download_excel_results(",".split(self.categories_str))
            
            st.write("You must download and review the Excel file before continuing.")
            st.write("Refresh the page to summarize the articles.")
       
    def summarize_articles(self):
        if self.df is not None:
              # file is uploaded and ready to categorize
            with st.spinner("Summarizing categories of manuscripts..."):
                markdown_to_convert = review_generate.summarize_all_categories(self.df, self.research_q)
                docx_data = convert_markdown_docx(markdown_to_convert)
                self._download_doc_results(docx_data)
                
class DraftReviewManager(CompileManager):
    def __init__(self, summaries, research_q):
        super().__init__(None)
        self.research_q = research_q
        self.summaries = summaries
        st.session_state['file_uploaded_draft'] = False  # Initiate a unique file_uploaded variable for drafting

    def get_filename(self):
        return review_config.SR_STEP5_FILENAME
    
    def get_download_button_label(self):
        return review_config.DOCX_DOWNLOAD_LABEL
    
    def _download_results(self, docx_data):
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_filename(),
            mime=review_config.DOCX_MIME  # correct MIME type for docx
        )
    
    def draft_review(self):
        if self.summaries is not None:
            st.session_state['file_uploaded_draft'] = True  # file is uploaded and ready to draft
            with st.spinner("Preparing first draft of article..."):
                markdown_to_convert = review_generate.write_first_draft(self.summaries, self.research_q)
                docx_data = convert_markdown_docx(markdown_to_convert)
                self._download_results(docx_data)