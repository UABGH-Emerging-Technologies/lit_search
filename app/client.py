import subprocess
import sys

import requests

import streamlit as st

# proof of concept for reading uploaded word docs and excel files just like in scoping review
# on server side, word docs is made a tempfile which is then converted to md by pypandoc
# on server side, excel is made a pandas dataframe.


def start_server():
    cmd = ["python3", "app/server.py"]
    return subprocess.Popen(cmd, shell=False)


def show_page():
    if "server_started" not in st.session_state:
        st.session_state["server_started"] = True
        server_process = start_server()

    # try block is just to make sure server and client shutdown on a ctrl+c.
    # Doing it this way just to make local testing easier.
    try:
        st.title("Document Processor")

        # Allow users to upload either Word or Excel files
        uploaded_file = st.file_uploader("Choose a file (Word or Excel)", type=["docx", "xlsx"])

        if uploaded_file is not None:
            # Prepare the file data to send to the server
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            # Post the file to the server and handle the response
            response = requests.post("http://localhost:8000/upload/", files=files)

            if response.status_code == 200:
                data = response.json()
                # Check if the response is for a Word or Excel file
                if "markdown" in data:
                    # Display the markdown text
                    st.markdown(data["markdown"])
                elif "first_row" in data:
                    # Display the first row of the Excel file
                    st.json(data["first_row"])
                else:
                    st.error("Received unexpected data format from server.")
            else:
                st.error("Failed to process file. Please ensure it is a valid document.")

    except KeyboardInterrupt:
        print("Interrupt received, shutting down the server...")
        server_process.terminate()
        sys.exit(0)


if __name__ == "__main__":
    show_page()
