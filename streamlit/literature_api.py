import streamlit as st
import requests
import base64
import os
from requests.exceptions import ConnectionError

API_BASE_URL = os.getenv("LIT_SEARCH_API_BASE_URL", "http://localhost:8000")


def initial_literature_search(research_question: str):
    """
    Perform the initial literature search by calling the API endpoint.
    Returns True if search finished successfully, False otherwise.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/search/v01/scoping/step1/",
            json={"research_question": research_question},
        )
        if response.status_code == 200:
            # Parse JSON response and decode base64 encoded Excel file
            json_response = response.json()
            encoded_xlsx = json_response.get("encoded_xlsx")
            if encoded_xlsx:
                decoded_bytes = base64.b64decode(encoded_xlsx)
                st.session_state["initial_search_result"] = decoded_bytes
                return True
            else:
                st.error("API response missing encoded_xlsx field.")
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except ConnectionError:
        st.error(f"Cannot connect to API server at {API_BASE_URL}. Please ensure the server is running.")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def iterate_search(uploaded_file, research_question: str):
    """
    Perform iterate search by calling the API endpoint.
    Returns True if search finished successfully, False otherwise.
    """
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {"research_question": research_question}
        response = requests.post(
            f"{API_BASE_URL}/search/v01/scoping/step2/iteration/",
            data=data,
            files=files,
        )
        if response.status_code == 200:
            json_response = response.json()
            encoded_xlsx = json_response.get("encoded_xlsx")
            if encoded_xlsx:
                import base64
                decoded_bytes = base64.b64decode(encoded_xlsx)
                st.session_state["iteration_search_result"] = decoded_bytes
                return True
            else:
                st.error("API response missing encoded_xlsx field.")
                return False
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def categorize_articles(uploaded_file, userdefined_categories: str):
    """
    Categorize articles by calling the API endpoint.
    Returns True if categorization finished successfully, False otherwise.
    """
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        import base64
        file_bytes = uploaded_file.getvalue()
        encoded_xlsx = base64.b64encode(file_bytes).decode("utf-8")
        json_data = {
            "user_defined_categories": userdefined_categories,
            "xlsx_encoded": encoded_xlsx,
        }
        response = requests.post(
            f"{API_BASE_URL}/search/v01/scoping/step3/",
            json=json_data,
        )
        if response.status_code == 200:
            json_response = response.json()
            encoded_xlsx = json_response.get("encoded_xlsx")
            if encoded_xlsx:
                decoded_bytes = base64.b64decode(encoded_xlsx)
                st.session_state["categorize_result"] = decoded_bytes
                return True
            else:
                st.error("API response missing encoded_xlsx field.")
                return False
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def summarize_categories(uploaded_file, research_question: str):
    """
    Summarize categories by calling the API endpoint.
    Returns True if summarization finished successfully, False otherwise.
    """
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        data = {"research_question": research_question}
        response = requests.post(
            f"{API_BASE_URL}/search/v01/scoping/step4/",
            data=data,
            files=files,
        )
        if response.status_code == 200:
            st.session_state["summarize_result"] = response.content
            return True
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


import base64

import base64

def draft_article(uploaded_file, research_question: str):
    """
    Draft article by calling the API endpoint.
    Returns decoded draft bytes if successful, None otherwise.
    """
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return None
    try:
        file_bytes = uploaded_file.getvalue()
        encoded_docx = base64.b64encode(file_bytes).decode("utf-8")
        json_data = {
            "research_question": research_question,
            "docx_encoded": encoded_docx,
        }
        response = requests.post(
            f"{API_BASE_URL}/search/v01/scoping/step5/",
            json=json_data,
        )
        if response.status_code == 200:
            response_json = response.json()
            encoded_docx_response = response_json.get("encoded_docx", None)
            if encoded_docx_response:
                draft_bytes = base64.b64decode(encoded_docx_response)
                return draft_bytes
            else:
                st.error("No draft document received from server.")
                return None
        else:
            st.error(f"API error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def generate_bibtex(uploaded_file):
    """
    Generate bibtex file by calling the API endpoint.
    Returns True if bibtex generation complete, False otherwise.
    """
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        import os
        import base64

        file_bytes = uploaded_file.getvalue()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")
        _, ext = os.path.splitext(uploaded_file.name)
        ext = ext.lower()

        json_data = {
            "file_encoded": encoded_file,
            "file_extension": ext,
        }

        response = requests.post(
            f"{API_BASE_URL}/search/v01/standalone/bibliography/",
            json=json_data,
        )
        if response.status_code == 200:
            st.session_state["bibtex_result"] = response.content
            return True
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False