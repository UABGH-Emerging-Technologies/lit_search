import ScopingReview.generate as review_generate
import pandas as pd
import streamlit as st

class CategorizeManager:
    def __init__(self, df, research_q):
        self.df = df
        self.research_q = research_q
        st.session_state['file_uploaded'] = False  # Initiate the file_uploaded variable

    def categorize_articles(self, input_text):
        if st.session_state['file_uploaded']:  # If the file is uploaded, then start categorizing
            with st.spinner("Categorizing contents of file..."):
                category_df = review_generate.categorize(self.df, input_text)
        else:
            uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])

            if uploaded_file is not None:
                self.df = pd.read_excel(uploaded_file)
                st.session_state['file_uploaded'] = True  # file is uploaded and ready to categorize               
                            
class SummarizeManager:
    def __init__(self, df, research_q):
        self.df = df
        self.research_q = research_q

    def summarize_articles(self):
        uploaded_file = st.file_uploader("Upload file with category labels", type=['xlsx'])

        if uploaded_file is not None:
            with st.spinner("Summarizing categories of manuscripts..."):
                summary_df = pd.read_excel(uploaded_file)
                
                if st.button('Summarize'):
                    summaries = review_generate.summarize(summary_df)