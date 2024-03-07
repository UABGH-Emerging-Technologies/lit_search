import streamlit as st
# import os
import pandas as pd
import ScopingReview.data as data

def show_scoping_review_page():
    st.set_page_config(
        page_title="Scoping Review",
        page_icon="💼",
    )
    
    st.title("Categorization")
    st.write("Brought to you by the Anesthesiology Development and Data Science teams")

    uploaded_file = st.file_uploader("Upload a file", type=['csv', 'xlsx'])

    # Neurological Disorders, Autoimmune Disorders, Renal Disorders, Other Conditions
    df = None

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    
    input_text = st.text_area("Enter your list of categorizes, separated by commas:")
    if input_text and df is not None:
        df = data.categorization(df, input_text)
    else:
        st.write("Please enter your list of values above.")
        
    if st.button("Download Excel File"):
            df.to_excel("step3result.xlsx", index=False)



    
if __name__ == "__main__":
    show_scoping_review_page()

