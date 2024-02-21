# streamlit_app.py

import streamlit as st

import datetime
import os

from llm_utils.sensitive import manage_sensitive
from llm_utils.database import get_db_connection
from llm_utils.streamlit_common import hide_streamlit_branding

from ScopingReview.generate import search_scoping_review_vectorstore, get_scoping_review_response
import ScopingReview_config.config as ScopingReview_config

def show_ScopingReview_page(vectorstore=ScopingReview_config.ScopingReview_VECTORSTORE):

    # page metadata
    st.set_page_config(
        page_title="ScopingReview ",
        page_icon="🤖",
    )
    # hide streamlit branding
    hide_streamlit_branding()

    # page content
    st.title("🗃️ ScopingReview 🤖")
    st.markdown("""
    **TODO - UPDATE THIS

    ---
    """)

    st.sidebar.markdown("""
    **Generative AIs are not reliable for factual information.**

    They are helpful for synthesis and idea generation. They are predicting a response to what you say based on their training material (in this case pages from the internet).

    You can trick generative AIs into saying whatever you want. If you succeed in tricking that AI, then what it says is something you created, not something it created.

    As always, use your best judgment. An AI can do the wrong thing at the worst time.
    """)

    with st.form(key="query_form"):
        user_question = st.text_input("Enter your research question:", "variability of lidocaine usage by race")
        submit_button = st.form_submit_button("Submit")

        if submit_button:
            with st.spinner("Thinking..."):
                submit_time = datetime.datetime.now()
                documents = search_ScopingReview_vectorstore(query=user_question, store=vectorstore)
                result = get_ScopingReview_response(query=user_question, docs=documents)
                response_time = datetime.datetime.now()
            st.markdown(result.content)
            
            try:
                with get_db_connection(db_server=ScopingReview_config.DB_SERVER,
                                       db_name=ScopingReview_config.DB_NAME,
                                       db_user=ScopingReview_config.DB_USER,
                                       db_password=ScopingReview_config.DB_PASSWORD) as conn:
                    # tempting to move this into llm_utils, but the query will be unique to each app.
                    cursor = conn.cursor()
                    query = """
                    INSERT INTO [dbo].[ScopingReview] (user_input, llm_response, request_sent, response_received)
                    VALUES (?, ?, ?, ?)
                    """

                    cursor.execute(query, (user_question, result.content, submit_time, response_time))

                    st.success("Success!")
            except Exception as e:
                st.error("Something went wrong, if the problem persists contact the developers")
                st.error(e)

if __name__ == "__main__":
    show_ScopingReview_config._page()
    
