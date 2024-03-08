import streamlit as st
import openai
import pandas as pd
import tempfile

# TODO: Let's call all of this "LiteratureReview" for long names and "lit" for short names
from llm_utils.database import get_db_connection
from llm_utils.streamlit_common import hide_streamlit_branding, apply_uab_font
from llm_utils.text_format import convert_markdown_docx
from llm_utils.call_pubmed_api import PubMedAPI
from llm_utils.prep_pubmed_query import PubMedQueryGenerator

import ScopingReview_config.app_config as review_app_config
import ScopingReview_config.config as review_config
import ScopingReview.generate as review_generate
import ScopingReview.data as review_data
from ScopingReview.data import make_and_refine_query, search_and_compile, write_excel_output
from ScopingReview.data import get_relevant_keywords, get_unique_keywords

import tempfile
from datetime import datetime

def show_literature_page():
    # page metadata
    st.set_page_config(
        page_title="Literature Search",
        page_icon="📚",
    )
    # hide streamlit branding
    hide_streamlit_branding()

    # apply uab font
    apply_uab_font()

    # page content
    st.title("📚 Literature Search 🤖")
    st.markdown("""
    **Use generative AI to situate your research question in the context of existing literature.**

    Brought to you by the Anesthesiology Research Support, Informatics, and Data Science teams.

    _Not approved for use with PHI._

    All submissions are recorded for potential review by departmental and health system personnel.

    ---
    """)

    search_type_options = [
        "assess the novelty of my idea",
        "get a jump start on my literature search",
        "estimate the complexity and feasibility of my idea",
        "identify weaknesses or gaps in the literature that serve as the key support for a proposed NIH-style grant",
        "work on scoping review"
    ]

    query_type = st.radio("Which of these best describes what you want help with?", search_type_options)
    research_q = st.text_area("Enter your research question/topic (or for a grant, your specific aims)",
                                "Retrospectively, In adult patients undergoing surgery, how does the use of regional anesthesia techniques compare to general anesthesia in terms of postoperative pain management?")


    if query_type == "work on scoping review":
        scoping_step = None
        scoping_steps = [
        "first search",
        "iterate on search",
        "categorize articles",
        "summarize categories",
        "draft article"
        ]
        scoping_step = st.radio("What step of the scoping review do you want to work on?", scoping_steps)
        
        # TODO: should go after each if ... button
        # input_time = datetime.now()
                    
        # Only need a pubmed search on step1 or step2
        if scoping_step not in scoping_steps[2:]:
            if st.button("Find Articles"):
                cost = 0.0
                input_time = datetime.now()
                article_ids=[]
                loop_counter = 0
                query = ""
                while len(article_ids)<review_config.MIN_ARTICLES and loop_counter<6:
                    with st.spinner("Generating pubmed search string."):
                        cost, loop_counter, query, search_string = make_and_refine_query(query, research_q, cost, loop_counter)
                    st.write(f"**Searching Pubmed with the query:** _{query}_")
                    with st.spinner("Searching Pubmed and compiling articles."):
                        pm_connection, article_ids = search_and_compile(query, article_ids)
                        articles_df = pm_connection.fetch_article_details(article_ids)
                        
                if scoping_step == "first search":
                    with st.spinner("Compiling articles"):
                        articles_df = review_data.make_initial_df(pm_connection, article_ids)
                    
                    # save with nice formatting
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
                        # Use the xlsxwriter engine
                        write_excel_output(tmpfile, articles_df, research_q)

                        # Read the file in binary mode for the download button
                        with open(tmpfile.name, "rb") as file:
                            st.download_button(
                                label="Download Excel file",
                                data=file,
                                file_name=review_config.SR_STEP1_FILENAME,
                                mime="application/vnd.ms-excel"
                            )
 
        if scoping_step == "iterate on serach":
            uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])

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

            
        if scoping_step == "categorize articles":
            uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])

            if uploaded_file is not None:
                category_df = pd.read_excel(uploaded_file)
                
                input_text = st.text_area("Enter your list of categories, separated by commas:", "Category 1, Category 2, etc...")

                if st.button('Categorize'):
                    cost = 0.0
                    input_list = input_text.split(',')
                    input_list = [value.strip() for value in input_list if value.strip()]
            
                    for index, row in category_df.iterrows():
                        data = row['abstract']
                        result = prompt.chat.invoke(prompt.chat_prompt.format_prompt(categories=input_list, context=data).to_messages())
                        category_df.at[index, 'category'] = result.content
                    
                    # save with nice formatting
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmpfile:
                        # Use the xlsxwriter engine
                        write_excel_output(tmpfile, category_df, research_q)

                        # Read the file in binary mode for the download button
                        with open(tmpfile.name, "rb") as file:
                            st.download_button(
                                label="Download Categorized File",
                                data=file,
                                file_name=review_config.SR_STEP3_FILENAME,
                                mime="application/vnd.ms-excel"
                            )

    else:
        if st.button("Search"):
            cost = 0.0
            article_ids = []
            loop_counter = 0
            previous_query = ""
            while len(article_ids)<review_config.MIN_ARTICLES and loop_counter<6:
                with st.spinner("Generating pubmed search string."):
                    query_maker = PubMedQueryGenerator(research_q)
                    search_string, response_meta = query_maker.generate_search_string(
                        PUBMED_CHAT = review_config.CHAT,
                        loop_n=loop_counter, 
                        last_query=previous_query
                        )
                    cost += response_meta.total_cost
                    previous_query = search_string
                    loop_counter += 1
                st.write(f"**Searching Pubmed with the query:** _{search_string}_")
                with st.spinner("Searching Pubmed."):
                    pm_connection = PubMedAPI(email=review_config.DEV_EMAIL, max_results=review_config.MAX_ARTICLES_LR, streamlit_context=True)
                    article_ids_new = pm_connection.search_pubmed_articles(search_string)
                    article_ids = list(set().union(article_ids, article_ids_new))
            if len(article_ids)>0:
                st.write("**Found the following articles:**")
                article_infos = ""
                bibliography = ""
                additional_articles = ""
                articles = pm_connection.fetch_article_details(article_ids)
                articles['pmid'] = articles['pmid'].astype(str)
                                
                for i, article in articles.iterrows():
                    print('article - ', article)
                    print('article authors - ', article['authors'])
                    formatted_article = article['citation']
                    reference = f"{formatted_article}\n\n"
                    if i < review_config.MIN_ARTICLES:
                        st.write(formatted_article)

                        article_info = f"Authors: {article['authors']}\nTitle: {article['title']}\nJournal: {article['journal']}\nPublication Year: {article['date_published']}\nAbstract: {article['abstract']}\nAPA Citation: {formatted_article}\n\n"
                        article_infos += article_info
                        bibliography += reference
                    elif i == review_config.MIN_ARTICLES:
                        st.write("**...and more, which will be included in the downloadable file.**")
                        additional_articles += reference
                    else: 
                        additional_articles += reference
                with st.spinner("Summarizing and evaluating novelty"):
                    overall_introduction, response_meta = review_generate.generate_overall_introduction(
                        research_q,
                        article_infos,
                        query_type
                        )
                response_time = datetime.now()
                cost += response_meta.total_cost
                output_text = ""
                output_text = overall_introduction + "\n\n" + "\n\n **Works considered in above text:**\n\n" + bibliography + "\n\n **Additional articles found:**\n\n" + additional_articles
                docx_data = convert_markdown_docx(output_text)

                if docx_data:
                    st.balloons()
                    st.write("Note that once you hit download, this form will reset.")

                    st.download_button(
                        label="Download Evaluation",
                        data=docx_data,
                        file_name="Literature_novelty_evaluation.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # correct MIME type for docx
                    )
            else:
                st.write("No articles found")

if __name__ == "__main__":
    
    show_literature_page()