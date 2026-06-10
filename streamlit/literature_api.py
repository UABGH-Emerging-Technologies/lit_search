import os
import io
import json
import base64
import requests
import pandas as pd
import streamlit as st
from requests.exceptions import ConnectionError

from aiweb_common.WorkflowHandler import manage_sensitive


# LLM credentials come from the shared secrets. manage_sensitive resolves, in order:
# /run/secrets/<name> (compose mount) -> /workspaces/*/secrets/<name>.txt (devcontainer)
# -> env var (.env / `make run`). So no .env is needed when the secrets are mounted.
API_KEY = manage_sensitive("azure_proxy_key")
AZURE_ENDPOINT = manage_sensitive("azure_proxy_endpoint")
MODEL_NAME = os.environ.get("OPENAI_COMPATIBLE_MODEL", "gpt-4o")

# Backend URL: defaults to the compose service name; localhost for non-docker dev.
API_BASE_URL = os.environ.get("LIT_ENDPOINT", "http://lit_api:8000")

DEFAULT_LLM_CONFIG = {
    "openai_compatible_endpoint": AZURE_ENDPOINT,
    "openai_compatible_model": MODEL_NAME
}


def get_auth_headers():
    """Get authorization headers with API key."""
    if API_KEY and API_KEY != "PUT_YOUR_API_KEY_HERE":
        return {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }
    return {}


def initial_literature_search(research_question: str):
    """Perform the initial literature search by calling the API endpoint."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/v01/scoping/step1/",
            json={
                "research_question": research_question,
                **DEFAULT_LLM_CONFIG
            },
            headers=get_auth_headers(),
        )
        if response.status_code == 200:
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


def initial_literature_search_summary(research_question: str):
    """Perform the initial literature search by calling the summary API endpoint."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/v01/standalone/summary/",
            json={
                "research_question": research_question,
                **DEFAULT_LLM_CONFIG
            },
            headers=get_auth_headers(),
        )
        if response.status_code == 200:
            json_response = response.json()
            encoded_docx = json_response.get("encoded_docx")
            if encoded_docx:
                decoded_bytes = base64.b64decode(encoded_docx)
                st.session_state["initial_search_summary_result"] = decoded_bytes
                st.session_state["search_finished"] = True
                return True
            else:
                st.error("API response missing encoded_docx field.")
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except ConnectionError:
        st.error(f"Cannot connect to API server at {API_BASE_URL}. Please ensure the server is running.")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def iterate_search(uploaded_file, research_question: str):
    """Perform iterate search by calling the API endpoint."""
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        # Encode file as base64 like all other functions
        file_bytes = uploaded_file.getvalue()
        encoded_xlsx = base64.b64encode(file_bytes).decode("utf-8")
        
        json_data = {
            "research_question": research_question,
            "primary_keywords": [],  
            "secondary_keywords": [],
            "exclusion_keywords": [],
            "xlsx_encoded": encoded_xlsx,
            **DEFAULT_LLM_CONFIG
        }
        
        response = requests.post(
            f"{API_BASE_URL}/v01/scoping/step2/iteration/",
            json=json_data,  
            headers=get_auth_headers(),  
        )
        
        if response.status_code == 200:
            json_response = response.json()
            encoded_xlsx = json_response.get("encoded_xlsx")
            if encoded_xlsx:
                decoded_bytes = base64.b64decode(encoded_xlsx)
                st.session_state["iteration_search_result"] = decoded_bytes
                return True
            else:
                st.error("API response missing encoded_xlsx field.")
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def categorize_articles(uploaded_file, userdefined_categories: str, research_question: str = ""):
    """Categorize articles by calling the API endpoint."""
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        file_bytes = uploaded_file.getvalue()
        encoded_xlsx = base64.b64encode(file_bytes).decode("utf-8")
        json_data = {
            "user_defined_categories": userdefined_categories,
            "xlsx_encoded": encoded_xlsx,
            "research_question": research_question, 
            **DEFAULT_LLM_CONFIG
        }
        response = requests.post(
            f"{API_BASE_URL}/v01/scoping/step3/",
            json=json_data,
            headers=get_auth_headers(),
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
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False


def summarize_categories(uploaded_file, research_question: str):
    """Summarize categories by calling the API endpoint."""
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False

    try:
        file_bytes = uploaded_file.getvalue()

        # Convert CSV to XLSX if needed
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
            xlsx_buf = io.BytesIO()
            df.to_excel(xlsx_buf, index=False)
            file_bytes = xlsx_buf.getvalue()

        # Encode XLSX for payload
        xlsx_encoded = base64.b64encode(file_bytes).decode("utf-8")
        payload = {
            "research_question": research_question,
            "xlsx_encoded": xlsx_encoded,
            **DEFAULT_LLM_CONFIG
        }

        resp = requests.post(
            f"{API_BASE_URL}/v01/scoping/step4/",
            headers=get_auth_headers(),
            json=payload,
        )

        if resp.status_code == 200:
            data = resp.json()
            encoded_docx = data.get("encoded_docx")
            if not encoded_docx:
                st.error("API response missing encoded_docx field.")
                return False

            st.session_state["docx_bytes"] = base64.b64decode(encoded_docx)

            warn = resp.headers.get("Warning", "")
            if warn:
                st.session_state["summarize_warning"] = warn

            return True

        st.error(f"API error: {resp.status_code} {resp.text}")
    except ConnectionError:
        st.error(f"Cannot connect to API server at {API_BASE_URL}. Please ensure the server is running.")
    except Exception as e:
        st.error(f"Request failed: {e}")

    return False


def draft_article(uploaded_file, research_question: str):
    """Draft article by calling the API endpoint."""
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return None
    try:
        file_bytes = uploaded_file.getvalue()
        encoded_docx = base64.b64encode(file_bytes).decode("utf-8")
        json_data = {
            "research_question": research_question,
            "docx_encoded": encoded_docx,
            **DEFAULT_LLM_CONFIG
        }
        response = requests.post(
            f"{API_BASE_URL}/v01/scoping/step5/",
            json=json_data,
            headers=get_auth_headers(),
        )
        if response.status_code == 200:
            response_json = response.json()
            encoded_docx_response = response_json.get("encoded_docx", None)
            if encoded_docx_response:
                return base64.b64decode(encoded_docx_response)
            else:
                st.error("No draft document received from server.")
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return None


def generate_bibtex(uploaded_file):
    """Generate bibtex file by calling the API endpoint."""
    if uploaded_file is None:
        st.write("Please upload a file before continuing...")
        return False
    try:
        file_bytes = uploaded_file.getvalue()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")
        _, ext = os.path.splitext(uploaded_file.name)
        ext = ext.lower()

        json_data = {
            "file_encoded": encoded_file,
            "file_extension": ext,
        }

        response = requests.post(
            f"{API_BASE_URL}/v01/standalone/bibliography/",
            json=json_data,
            headers=get_auth_headers(),
        )
        if response.status_code == 200:
            st.session_state["bibtex_result"] = response.content
            return True
        else:
            st.error(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return False