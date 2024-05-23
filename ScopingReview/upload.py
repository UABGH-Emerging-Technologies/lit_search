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
    async def read_file(self, file: UploadFile) -> Tuple[Union[pd.DataFrame, str], str]:
        try:
            extension = Path(file.filename).suffix
            print("Extension - ", extension)
            contents = await file.read()  # Read the content asynchronously

            if extension == ".xlsx":
                print("Opening Excel file")
                # looks like for async, you need explicit tuples in return
                return (pd.read_excel(BytesIO(contents)), extension)
            elif extension == ".docx":
                print("Opening Word file")
                with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmpfile:
                    tmpfile.write(contents)
                    md = pypandoc.convert_file(tmpfile.name, "markdown")
                    return (md, extension)
            else:
                return (None, None)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid file format or corrupted file.") from e

    async def upload_file(self, upload_file: UploadFile) -> Tuple[Union[pd.DataFrame, str], str]:
        out = await self.read_file(upload_file)
        return out[0], out[1]
