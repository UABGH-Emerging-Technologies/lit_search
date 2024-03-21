import streamlit as st
import pandas as pd
import tempfile
import pypandoc
from pathlib import Path

class UploadManager:
    def __init__(self, message:str, file_types:list):
        self.message = message
        self.file_types = file_types
        
    def _get_file_extension(self):
        extension = Path(self.uploaded_file.name).suffix
        return extension
        
    def upload_file(self):
        self.uploaded_file = st.file_uploader(self.message, type=self.file_types)
        if self.uploaded_file is not None:
            extension = self._get_file_extension()
            if extension == '.xlsx':
                return pd.read_excel(self.uploaded_file), extension
            elif extension == '.docx':
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                    tmpfile.write(self.uploaded_file.getvalue())
                    return pypandoc.convert_file(tmpfile.name, 'markdown'), extension
        return None, None