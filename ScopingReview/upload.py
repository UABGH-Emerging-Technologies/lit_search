import tempfile
from pathlib import Path
import pandas as pd
import pypandoc
import streamlit as st
from fastapi import UploadFile, HTTPException
from io import BytesIO
import pandas as pd
import tempfile
import pypandoc
from typing import Union, Tuple

class BaseUploadManager:
    def __init__(self, message: str, file_types: list):
        print("Initializing Upload Manager")
        self.message = message
        self.file_types = file_types

    def read_file(self, file):
        extension = Path(file.name).suffix
        print("Extension - ", extension)
        if extension == ".xlsx":
            print("Opening Excel file")
            return pd.read_excel(file), extension
        elif extension == ".docx":
            print("Opening Word file")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(file.getvalue())
                return pypandoc.convert_file(tmpfile.name, "markdown"), extension
        return None, None


# name for compataibility, will want StreamlitUploadManager eventually
class UploadManager(BaseUploadManager):
    def upload_file(self):
        self.uploaded_file = st.file_uploader(self.message, type=self.file_types)
        if self.uploaded_file is not None:
            return self.read_file(self.uploaded_file)
        else:
            st.write("Please upload a file to continue...")
            return None, None


class FastAPIUploadManager(BaseUploadManager):
    def read_file(self, file_bytes: bytes, extension: str) -> Union[pd.DataFrame, str]:
        """
        Reads the file from byte string based on the file extension and returns
        either a DataFrame or a markdown string.
        
        Args:
            file_bytes (bytes): The byte-encoded content of the file.
            extension (str): The file extension indicating the file type.

        Returns:
            Union[pd.DataFrame, str]: Depending on the file extension, either returns a DataFrame for Excel files
            or a markdown string for DOCX files.

        Raises:
            HTTPException: If the file format is unsupported or if an error occurs during processing.
        """
        try:
            print("Processing file with extension - ", extension)
            
            if extension == ".xlsx":
                print("Opening Excel file")
                return pd.read_excel(BytesIO(file_bytes))
            elif extension == ".docx":
                print("Converting Word file to Markdown")
                with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmpfile:
                    tmpfile.write(file_bytes)
                    tmpfile.seek(0)
                    return pypandoc.convert_file(tmpfile.name, "markdown")
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file extension: {extension}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid file format or corrupted file: {str(e)}")
