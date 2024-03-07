import streamlit as st
from langchain_openai import AzureChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import pandas as pd
import ScopingReview_config.config as review_config
from ScopingReview import prompts
from datetime import datetime
import tempfile

from ScopingReview.data import make_and_refine_query, search_and_compile, write_excel_output
from ScopingReview.data import get_relevant_keywords, get_unique_keywords
    
def show_professional_development_page():
    st.set_page_config(
        page_title="Scoping Review",
        page_icon="💼",
    )
    
    st.title("💼 Iterating 🤖")
    st.write("Brought to you by the Anesthesiology Data Science team")


    uploaded_file = st.file_uploader("Upload a file", type=['csv', 'xlsx'])
     
    system_template = prompts.ITER_PUBMED_PROMPT

    human_template = """
    CONTEXT:
    {context}

    OUTPUT:
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        keywords_to_requery = get_relevant_keywords(df)
        unique_keywords_str = get_unique_keywords(keywords_to_requery)
        
        if st.button("ReSearch"):
            article_ids = []
            loop_counter = 0
            cost = 0.0
            query = ""
            while len(article_ids)<review_config.MIN_ARTICLES and loop_counter<6:
                with st.spinner("Generating pubmed search string."):
                    cost, loop_counter, query, _ = make_and_refine_query(query, unique_keywords_str, cost, loop_counter)
                st.write(f"**Searching Pubmed with the query:** _{query}_")
                
            with st.spinner("Searching Pubmed and compiling articles."):
                pm_connection, article_ids = search_and_compile(query, article_ids)
                articles_df = pm_connection.fetch_article_details(article_ids)
                print('articles_df - ', articles_df)
           
            # save with nice formatting
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
                # Use the xlsxwriter engine
                write_excel_output(tmpfile, articles_df, unique_keywords_str)
                # Read the file in binary mode for the download button
                with open(tmpfile.name, "rb") as file:
                    st.download_button(
                        label="Download Excel file",
                        data=file,
                        file_name=review_config.SR_STEP2_FILENAME,
                        mime="application/vnd.ms-excel"
                    )                         

if __name__ == "__main__":
    show_professional_development_page()

