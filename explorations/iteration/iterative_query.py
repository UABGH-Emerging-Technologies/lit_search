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
from llm_utils.call_pubmed_api import PubMedAPI

def show_professional_development_page():
    st.set_page_config(
        page_title="Scoping Review",
        page_icon="💼",
    )
    
    st.title("💼 Iterating 🤖")
    st.write("Brought to you by the Anesthesiology Data Science team")


    uploaded_file = st.file_uploader("Upload a file", type=['csv', 'xlsx'])


    system_template = """Help categorize the abstracts into either of the input categories given by the user and return only 1 category as output(whichever matches the most)."""


    human_template = """
    CONTEXT:
    {context}

    INPUT CATEGORIES:
    {categories}

    OUTPUT:
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        input_text = st.text_area("Enter your list of values, separated by commas:")

        if input_text:
            input_list = input_text.split(',')
            input_list = [value.strip() for value in input_list if value.strip()]

            for index, row in df.iterrows():
                data = row['abstract']
                result = review_config.CHAT.invoke(chat_prompt.format_prompt(categories=input_list, context=data).to_messages())
                df.at[index, 'category'] = result.content
                
                        
            print(df["category"])
            
        else:
            st.write("Please enter your list of values above.")

    
    if st.button("Download Excel File"):
            df.to_excel("result.xlsx", index=False)



    
if __name__ == "__main__":
    show_professional_development_page()

