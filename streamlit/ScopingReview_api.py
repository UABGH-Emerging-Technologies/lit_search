import streamlit as st
from datetime import datetime
from aiweb_common.streamlit.streamlit_common import apply_uab_font, hide_streamlit_branding
from literature_api import (
    initial_literature_search,
    iterate_search,
    categorize_articles,
    summarize_categories,
    draft_article,
    generate_bibtex
)

def show_literature_search_page():
    page_title = "Literature Search"
    page_icon = "📚"
    search_type_options = ["initial literature search", "work on scoping review"]
    scoping_steps = [
        "first search",
        "iterate on search",
        "categorize articles",
        "summarize categories",
        "draft article",
        "generate bibtex file",
    ]

    st.set_page_config(page_title=page_title, page_icon=page_icon)
    hide_streamlit_branding()
    apply_uab_font()

    st.title(f"{page_icon} {page_title} 🤖")
    st.markdown(
        """
        **Use generative AI to situate your research question in the context of existing literature.**

        Brought to you by the Anesthesiology Research Support, Informatics, and Data Science teams.

        _Not approved for use with PHI._

        All submissions are recorded for potential review by departmental and health system personnel.

        ---
        """
    )

    prev_query_type = st.session_state.get("prev_query_type", None)
    query_type = st.radio("Which of these best describes what you want help with?", search_type_options)
    if prev_query_type != query_type:
        st.session_state["button_clicked"] = False
        st.session_state["search_finished"] = False
        st.session_state["prev_query_type"] = query_type

    # Store research_q in session_state
    if "research_q" not in st.session_state:
        st.session_state["research_q"] = ""
    st.session_state["research_q"] = st.text_area(
        "Enter your research question/topic (or for a grant, your specific aims)",
        value=st.session_state["research_q"],
        placeholder="Enter your research question here and press Ctrl+Enter or click outside the text box to update.",
    )
    research_q = st.session_state["research_q"]

    if "prev_research_q" not in st.session_state or st.session_state["prev_research_q"] != research_q:
        st.session_state["button_clicked"] = False
        st.session_state["search_finished"] = False
        st.session_state["prev_research_q"] = research_q

    if query_type == "work on scoping review":
        scoping_step = st.radio("What step of the scoping review do you want to work on?", scoping_steps)
        if "prev_scoping_step" not in st.session_state or st.session_state["prev_scoping_step"] != scoping_step:
            st.session_state["button_clicked"] = False
            st.session_state["search_finished"] = False
            st.session_state["prev_scoping_step"] = scoping_step

        if research_q == "":
            st.warning("Please enter a research question to continue")
        else:
            if scoping_step == "first search":
                if not st.session_state.get("button_clicked", False):
                    if st.button("Fetch Articles"):
                        finished = initial_literature_search(research_q)
                        if finished:
                            st.session_state["search_finished"] = True
                            st.session_state["button_clicked"] = True
                else:
                    finished = st.session_state.get("search_finished", False)
                    if finished:
                        st.session_state["search_finished"] = True
                        st.session_state["button_clicked"] = True

            elif scoping_step == "iterate on search":
                uploaded_file = st.file_uploader("Upload Excel File with Y/N selection", type=["xlsx"])
                if not st.session_state.get("button_clicked", False):
                    if st.button("Run Iteration Search"):
                        finished = iterate_search(uploaded_file, research_q)
                        if finished:
                            st.session_state["search_finished"] = True
                            st.session_state["button_clicked"] = True

                if st.session_state.get("search_finished", False):
                    excel_bytes = st.session_state.get("iteration_search_result", None)
                    if excel_bytes:
                        st.success("Iteration search completed successfully!")
                        st.download_button(
                            label="Download Excel Results",
                            data=excel_bytes,
                            file_name="iteration_search_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    else:
                        st.info("No iteration search results available for download yet.")

            elif scoping_step == "categorize articles":
                uploaded_file = st.file_uploader("Upload Excel File with Y/N selection for Categorization", type=["xlsx"])
                userdefined_categories = st.text_area(
                    "Enter your list of categories, separated by commas:",
                    "Category 1, Category 2, etc...",
                )
                finished = categorize_articles(uploaded_file, userdefined_categories)
                if finished:
                    st.session_state["categorization_finished"] = True
                    st.session_state["button_clicked"] = True

                if st.session_state.get("categorization_finished", False):
                    excel_bytes = st.session_state.get("categorize_result", None)
                    if excel_bytes:
                        st.success("Categorization completed successfully!")
                        st.download_button(
                            label="Download Categorized Excel Results",
                            data=excel_bytes,
                            file_name="categorized_articles.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    else:
                        st.info("No categorization results available for download yet.")

            elif scoping_step == "summarize categories":
                import base64
                import json
                import requests
                import pandas as pd
                import io

                uploaded_file = st.file_uploader("Upload Excel or CSV file with Category labels to summarize", type=["xlsx", "csv"])

                if uploaded_file is not None:
                    st.write("File uploaded:", uploaded_file.name)
                    file_bytes = uploaded_file.read()

                    if uploaded_file.type == "text/csv" or uploaded_file.name.endswith(".csv"):
                        df = pd.read_csv(io.BytesIO(file_bytes))
                        excel_buffer = io.BytesIO()
                        df.to_excel(excel_buffer, index=False)
                        file_bytes = excel_buffer.getvalue()

                    xlsx_encoded = base64.b64encode(file_bytes).decode("utf-8")
                    payload = {
                        "research_question": research_q,
                        "xlsx_encoded": xlsx_encoded,
                    }

                    if not st.session_state.get("button_clicked", False):
                        if st.button("Summarize Categories"):
                            with st.spinner("Summarizing articles..."):
                                api_url = "http://localhost:8000/search/v01/scoping/step4/"
                                headers = {"Content-Type": "application/json"}
                                response = requests.post(api_url, headers=headers, data=json.dumps(payload))

                                if response.status_code == 200:
                                    response_json = response.json()
                                    encoded_docx = response_json.get("encoded_docx", None)
                                    warning_msg = response.headers.get("Warning", "")
                                    if encoded_docx:
                                        docx_bytes = base64.b64decode(encoded_docx)
                                        st.session_state["summarization_finished"] = True
                                        st.session_state["button_clicked"] = True
                                        st.session_state["docx_bytes"] = docx_bytes
                                        if warning_msg:
                                            st.warning(warning_msg)
                                    else:
                                        st.error("No summary document received from server.")
                                else:
                                    st.error(f"Summarization failed: {response.status_code} {response.text}")

                if st.session_state.get("summarization_finished", False):
                    if "docx_bytes" in st.session_state:
                        st.success("Summarization completed successfully!")
                        st.download_button(
                            label="Download Summary DOCX",
                            data=st.session_state["docx_bytes"],
                            file_name="summary_categories.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    else:
                        st.info("No summarization results available for download yet.")

            elif scoping_step == "draft article":
                uploaded_file = st.file_uploader("Upload document of summaries to draft scoping review", type=["docx"])
                draft_bytes = draft_article(uploaded_file, research_q)
                if draft_bytes is not None:
                    st.session_state["draft_result"] = draft_bytes
                    st.session_state["draft_complete"] = True
                    st.session_state["button_clicked"] = True

                if st.session_state.get("draft_complete", False):
                    st.success("Drafting completed successfully!")
                    st.download_button(
                        label="Download Draft DOCX",
                        data=st.session_state["draft_result"],
                        file_name="draft_review.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

            elif scoping_step == "generate bibtex file":
                uploaded_file = st.file_uploader("Upload Finalized Excel sheet (CategorizeArticles.xlsx)", type=["xlsx", "docx"])
                finished = generate_bibtex(uploaded_file)
                if finished:
                    st.session_state["bibtex_complete"] = True
                    st.session_state["button_clicked"] = True

                if st.session_state.get("bibtex_complete", False):
                    bibtex_bytes = st.session_state.get("bibtex_result", None)
                    if bibtex_bytes:
                        st.success("Bibtex generation completed successfully!")
                        st.download_button(
                            label="Download Bibtex File",
                            data=bibtex_bytes,
                            file_name="bibliography.bib",
                            mime="application/x-bibtex",
                        )
                    else:
                        st.info("No bibtex results available for download yet.")

            # Download button for first search results
            if scoping_step == "first search":
                finished = st.session_state.get("search_finished", False)
                if finished:
                    excel_bytes = st.session_state.get("initial_search_result", None)
                    if excel_bytes:
                        st.success("Search completed successfully!")
                        st.download_button(
                            label="Download Excel Results",
                            data=excel_bytes,
                            file_name="literature_search_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    else:
                        st.error("No search results available for download.")

    else:
        # initial literature search outside scoping review
        if st.button("Fetch Articles"):
            finished = initial_literature_search(research_q)
            if finished:
                st.session_state["search_finished"] = True
            else:
                st.error("Failed to generate search results.")

        finished = st.session_state.get("search_finished", False)
        if finished:
            excel_bytes = st.session_state.get("initial_search_result", None)
            if excel_bytes:
                st.success("Search completed successfully!")
                st.download_button(
                    label="Download Excel Results",
                    data=excel_bytes,
                    file_name="literature_search_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.error("No search results available for download.")
        else:
            st.info("Click 'Fetch Articles' to perform the search and generate results.")


if __name__ == "__main__":
    show_literature_search_page()