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
    async def read_file(self, file: UploadFile):
        try:
            extension = Path(file.filename).suffix
            print("Extension - ", extension)
            contents = await file.read()  # Read the content asynchronously

            if extension == ".xlsx":
                print("Opening Excel file")
                return pd.read_excel(BytesIO(contents))
            elif extension == ".docx":
                print("Opening Word file")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                    tmpfile.write(contents)
                    return pypandoc.convert_file(tmpfile.name, "markdown")
            else:
                return None
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid file format or corrupted file.") from e
        finally:
            await file.close()  # Ensure to close the file after reading

    async def upload_file(self, upload_file: UploadFile):
        return await self.read_file(upload_file)
