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
import ScopingReview.utils as review_utils
import ScopingReview.step3prompt as prompt

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


        cost = 0.0
        input_time = datetime.now()
        # if not scoping or one of first two scoping steps, you'll do a pubmed search
        if scoping_step not in scoping_steps[2:]:
            if st.button('Search'):
                article_ids = []
                loop_counter = 0
                previous_query = ""
                while len(article_ids)<review_config.MIN_ARTICLES and loop_counter<6:
                    with st.spinner("Generating pubmed search string."):
                        query_maker = PubMedQueryGenerator(research_q)
                        search_string, response_meta = query_maker.generate_search_string(
                            PUBMED_CHAT=review_config.CHAT,
                            loop_n=loop_counter, 
                            last_query=previous_query
                            )
                        cost += response_meta.total_cost
                        previous_query = search_string
                        loop_counter += 1
                    st.write(f"**Searching Pubmed with the query:** _{search_string}_")
                    with st.spinner("Searching Pubmed."):
                        pm_connection = PubMedAPI(email="rmelvin@uabmc.edu", max_results=review_config.MAX_ARTICLES, streamlit_context=True)
                        article_ids_new = pm_connection.search_pubmed_articles(search_string)
                        article_ids = list(set().union(article_ids, article_ids_new))
                
                if scoping_step == "first search":
                    with st.spinner("Compiling articles"):
                        st.markdown("scoping review!")
                        articles_df = review_data.make_initial_df(pm_connection, article_ids)
                        
                    # save with nice formatting
                    with tempfile.NamedTemporaryFile(delete=True, suffix='.xlsx') as tmpfile:
                        review_utils.make_downloadable_excel(tmpfile, articles_df, sheet2_text=None)

                        # Read the file in binary mode for the download button
                        with open(tmpfile.name, "rb") as file:
                            st.download_button(
                                label="Download Excel file",
                                data=file,
                                file_name="articles.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                    
        if scoping_step == "categorize articles":
            uploaded_file = st.file_uploader("Upload file with Y/N filled in", type=['xlsx'])

            if uploaded_file is not None:
                category_df = pd.read_excel(uploaded_file)
                
                input_text = st.text_area("Enter your list of categories, separated by commas:")

                if input_text and st.button('Categorize'):
                    input_list = input_text.split(',')
                    input_list = [value.strip() for value in input_list if value.strip()]

                    for index, row in category_df.iterrows():
                        data = row['abstract']
                        result = prompt.chat.invoke(prompt.chat_prompt.format_prompt(categories=input_list, context=data).to_messages())
                        category_df.at[index, 'category'] = result.content
                            # save with nice formatting
                            
                    with tempfile.NamedTemporaryFile(delete=True, suffix='.xlsx') as tmpfile:
                        review_utils.make_downloadable_excel(tmpfile, category_df, sheet2_text=None)

                        # Read the file in binary mode for the download button
                        with open(tmpfile.name, "rb") as file:
                            st.download_button(
                                label="Download Categorized File",
                                data=file,
                                file_name="catgegorized_articles.xlsx",
                                mime="application/vnd.ms-excel"
                            )

        if query_type != "work on scoping review":
            if len(article_ids)>0:
                st.write("**Found the following articles:**")
                article_infos = ""
                bibliography = ""
                additional_articles = ""
                articles = pm_connection.fetch_article_details_medline(article_ids)
                for i, article in enumerate(articles):
                    formatted_aricle = articles.format_apa_citation(article,  article_ids[i])
                    if i < review_config.MIN_ARTICLES:
                        st.write(formatted_aricle)
                        article_info = f"Authors: {authors}\nTitle: {title}\nJournal: {journal}\nPublication Year: {pub_year}\nAbstract: {abstract}\nAPA Citation: {apa_citation}\n\n"
                        article_infos += article_info
                        bibliography += reference
                    elif i == review_config.MIN_ARTICLES:
                        st.write("**...and more, which will be included in the downloadable file.**")
                        additional_articles += reference
                    else: 
                        additional_articles += reference
                with st.spinner("Summarizing and evaluating novelty"):
                    overall_introduction, response_meta = irb_generate.generate_overall_introduction(
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

        # try:
        #     with get_db_connection(db_server=lit_app_config.DB_SERVER,
        #                             db_name=lit_app_config.DB_NAME,
        #                             db_user=lit_app_config.DB_USER,
        #                             db_password=lit_app_config.DB_PASSWORD) as conn:
        #         # tempting to move this into llm_utils, but the query will be unique to each app.
        #         cursor = conn.cursor()
        #         query = """
        #                 INSERT INTO [dbo].[literature_helper] (
        #                     email_address, 
        #                     research_idea, 
        #                     purpose_request, 
        #                     citations, 
        #                     literature_summary, 
        #                     pubmed_query, 
        #                     input_time, 
        #                     response_time,
        #                     total_cost
        #                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        #                 """

        #         cursor.execute(
        #             query,
        #             (
        #                 email,
        #                 research_q,
        #                 query_type,
        #                 bibliography + "\n\n" + additional_articles,
        #                 overall_introduction,
        #                 search_string,
        #                 input_time,
        #                 response_time,
        #                 cost
        #             )
        #         )
        #     st.success("To comply with a Health System Information Security request, submissions are recorded for potential review.")
        # except Exception as e:
        #     st.error("Something went wrong, and your submission was not recorded for review. Give the following message when asking for help.")
        #     st.error(e)


if __name__ == "__main__":
    show_literature_page()