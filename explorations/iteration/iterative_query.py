import streamlit as st
from langchain_openai import AzureChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os
import pandas as pd
import ScopingReview_config.config as review_config
from ScopingReview import prompts
from llm_utils.call_pubmed_api import PubMedAPI
from llm_utils.prep_pubmed_query import PubMedQueryGenerator
from datetime import datetime
import tempfile

# Function to check if either of the values is a 'Yes'
def check_relevance(row):
    author1_relevant = str(row["Author 1: Relevant Article? (Yes/No)"]).lower() in ["yes", "y", "true", "t"]
    author2_relevant = str(row["Author 2: Relevant Article? (Yes/No)"]).lower() in ["yes", "y", "true", "t"]

    if author1_relevant or author2_relevant:
        return row['keywords']
    else:
        return None

def get_relevant_keywords(df):
    df['Relevant Keywords'] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=['Relevant Keywords'])
    return relevant_df

def get_unique_keywords(df):
    df['Relevant Keywords'] = df.apply(check_relevance, axis=1)
    relevant_df = df.dropna(subset=['Relevant Keywords'])

    # Join all keywords into a single string, then split by comma
    all_keywords = ",".join(relevant_df['Relevant Keywords']).split(',')

    # Remove leading/trailing white spaces and convert to lower case
    all_keywords = [keyword.strip().lower() for keyword in all_keywords]

    # Get unique keywords
    unique_keywords = list(set(all_keywords))
    # Convert list of unique keywords to a comma-separated string
    unique_keywords_str = ", ".join(unique_keywords)

    return unique_keywords_str

def make_and_refine_query(cost, loop_counter, previous_query, unique_keywords_str):
    query_maker = PubMedQueryGenerator(unique_keywords_str)
    search_string, response_meta = query_maker.generate_search_string(
        PUBMED_CHAT = review_config.CHAT,
        loop_n=loop_counter, 
        last_query=previous_query
        )
    cost += response_meta.total_cost
    previous_query = search_string
    loop_counter += 1
    return cost, loop_counter, previous_query

def search_and_compile(query, article_ids):
    pm_connection = PubMedAPI(email=review_config.DEV_EMAIL, max_results=review_config.MAX_ARTICLES_SR, streamlit_context=True)
    article_ids_new = pm_connection.search_pubmed_articles(query)
    article_ids = list(set().union(article_ids, article_ids_new))
    articles_df = pm_connection.fetch_article_details(article_ids)
    return articles_df

def write_excel_output(tmpfile, articles_df, unique_keywords_str):
    with pd.ExcelWriter(tmpfile.name, engine='xlsxwriter') as writer:
        articles_df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Convert string to dataFrame and save to excel
        df_keywords = pd.DataFrame([unique_keywords_str], columns=['Unique Keywords'])
        df_keywords.to_excel(writer, index=False, sheet_name='Sheet2')

        # Get the xlsxwriter workbook and worksheet objects
        workbook  = writer.book
        worksheet1 = writer.sheets['Sheet1']
        worksheet2 = writer.sheets['Sheet2']
        # Define a format with word wrap
        wrap_format = workbook.add_format({'text_wrap': True})

        # Iterate over the DataFrame columns to set the column width
        for idx, col in enumerate(articles_df.columns):
            # Find the maximum length of data in the column
            column_len = articles_df[col].astype(str).map(len).max()
            column_title_len = len(col)
            max_len = min(100,max(column_len, column_title_len))

            # Set the column width with some extra margin
            worksheet1.set_column(idx, idx, max_len + 1, wrap_format)
    
        # You can also set column width for the second sheet if needed
        worksheet2.set_column(0, 0, len('Unique Keywords') + 1, wrap_format)
        
    
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
            cost = 0.0
            input_time = datetime.now()
            article_ids = []
            loop_counter = 0
            query = ""
            while len(article_ids)<review_config.MIN_ARTICLES and loop_counter<6:
                with st.spinner("Generating pubmed search string."):
                    cost, loop_counter, query = make_and_refine_query(cost, loop_counter, query, unique_keywords_str)
                st.write(f"**Searching Pubmed with the query:** _{query}_")
                
            with st.spinner("Searching Pubmed and compiling articles."):
                articles_df = search_and_compile(query, article_ids)
            
            # add author response column
            articles_df.insert(0, 'Author 1: Relevant Article? (Yes/No)', 'No')  
            articles_df.insert(1, 'Author 2: Relevant Article? (Yes/No)', 'No')  
            
            # temporary, add column for link and full text available
            articles_df['Full Text Link'] = "a link will go here"
            articles_df['AI Can Read Full Text?'] = "Yes"
            
            # save with nice formatting
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
                # Use the xlsxwriter engine
                write_excel_output(tmpfile, articles_df, unique_keywords_str)
                # Read the file in binary mode for the download button
                with open(tmpfile.name, "rb") as file:
                    st.download_button(
                        label="Download Excel file",
                        data=file,
                        file_name=review_config.SR_OUTPUT_FILENAME,
                        mime="application/vnd.ms-excel"
                    )                         
            
        # else:
        #     st.write("Please enter your list of values above.")

    
    # if st.button("Download Excel File"):
    #         df.to_excel("result.xlsx", index=False)



    
if __name__ == "__main__":
    show_professional_development_page()

