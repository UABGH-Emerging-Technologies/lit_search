import ScopingReview.generate as review_generate
import pandas as pd
import streamlit as st

class CategorizeManager:
    def __init__(self, df, research_q):
        self.df = df
        self.research_q = research_q

    def categorize_articles(self):
        uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])

        if uploaded_file is not None:
            with st.spinner("Categorizing contents of file..."):
                category_df = pd.read_excel(uploaded_file)
                
                input_text = st.text_area("Enter your list of categories, separated by commas:", "Category 1, Category 2, etc...")

                if st.button('Categorize'):
                    category_df = review_generate.categorize(category_df, input_text)                  
                            
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