import streamlit as st
from langchain_openai import AzureChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os
import pandas as pd
import ScopingReview.step3prompt as prompt

def show_scoping_review_page():
    st.set_page_config(
        page_title="Scoping Review",
        page_icon="💼",
    )
    
    st.title("Categorization")
    st.write("Brought to you by the Anesthesiology Development and Data Science teams")
# Upload
# categorizes request
# categorize
# Output

    uploaded_file = st.file_uploader("Upload a file", type=['csv', 'xlsx'])

    # categories = [Neurological Disorders, Autoimmune Disorders, Renal Disorders, Other Conditions]

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        input_text = st.text_area("Enter your list of categorizes, separated by commas:")

        if input_text:
            input_list = input_text.split(',')
            input_list = [value.strip() for value in input_list if value.strip()]

            for index, row in df.iterrows():
                data = row['abstract']
                result = prompt.chat.invoke(prompt.chat_prompt.format_prompt(categories=input_list, context=data).to_messages())
                df.at[index, 'category'] = result.content
                
                        
            # print(df["category"])
            
        else:
            st.write("Please enter your list of values above.")

    
    if st.button("Download Excel File"):
            df.to_excel("step3result.xlsx", index=False)



    
if __name__ == "__main__":
    show_scoping_review_page()

