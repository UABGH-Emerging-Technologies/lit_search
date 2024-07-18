import os
import datetime
import pandas as pd 
import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager
import streamlit as st
from aiweb_common.file_operations.file_handling import convert_markdown_docx

import tempfile

# The `SummarizeManager` class provides methods for managing and saving newsletter data, as well as
# checking for categories exceeding a specified threshold in a DataFrame.
class SummarizeManager(BaseManager):
    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q
        self.categories = []
        self.categories_str = ""

    def get_filename(self):
        raise NotImplementedError("This method must be implemented by subclasses.")

    def get_mime_type(self):
        raise NotImplementedError("This method must be implemented by subclasses.")


    def save_newsletter(self, docx_data, category, output_folder):
        """
        The function `save_newsletter` saves a Word document with the provided data in a specified output
        folder with a filename based on the category and current date.
        
        Args:
          docx_data: The `docx_data` parameter in the `save_newsletter` function is the binary data of a
        Word document (`.docx` file) that you want to save to a specific location on your system. This data
        represents the content of the newsletter that you want to store as a file.
          category: The `category` parameter in the `save_newsletter` function represents the category or
        topic of the newsletter that is being saved. It is used in formatting the filename of the saved
        document along with the current date.
          output_folder: The `output_folder` parameter in the `save_newsletter` function is the directory
        path where the newsletter document will be saved. If the specified folder does not exist, the
        function will create it before saving the document.
        """
        # Ensure the output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Format the filename
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"{category}_{today_date}.docx"
        file_path = os.path.join(output_folder, filename)

        # Save the document
        with open(file_path, "wb") as file:
            file.write(docx_data)
        print(f"File saved: {file_path}")
       
    @staticmethod 
    def categories_limit_check(df):
        """
        The `categories_limit_check` function checks for categories exceeding a specified threshold in a
        DataFrame.
        
        Args:
          df: The `df` parameter in the `categories_limit_check` method is expected to be a DataFrame
        containing a column named "category" that stores categories as strings separated by commas and
        spaces (", "). The method splits the categories, counts the occurrences of each unique category,
        and checks if any category count exceeds
        
        Returns:
          The `categories_limit_check` method returns a list of categories that exceed a specified
        threshold count (defined in `config.SUBCLASS_THRESHOLD`) based on the input DataFrame `df`.
        """
        categories_exceeding_limit = []
        if df is not None:
            df["category"] = df["category"].str.split(", ")
            df_exploded = df.explode("category")

            unique_values_counts = df_exploded["category"].value_counts()
            # print(unique_values_counts)
            for category, count in unique_values_counts.items():
                if count > config.SUBCLASS_THRESHOLD:
                    categories_exceeding_limit.append(category)
        # Note that in Python, empty lists return False in boolean checks
        return categories_exceeding_limit

# keeping name for compatibility with previous implementations
# eventually want this name to begin with Streamlit...
class StreamlitSummarizeManager(SummarizeManager):
    def __init__(self, df, research_q):
        super().__init__(df, research_q)
        st.session_state["file_uploaded_sum"] = False  # Initialize session state for summarization

    def get_doc_filename(self):
        return config.SR_STEP4_DOCX_FILENAME

    def get_excel_filename(self):
        return config.SR_STEP4_EXCEL_FILENAME

    def get_download_button_label(self):
        return config.BOTH_FILES

    def get_mime_type(self):
        return config.DOCX_MIME

    def download_doc_results(self, docx_data):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_doc_filename(),
            mime=self.get_mime_type(),
        )

class FastAPISummarizeManager(SummarizeManager):
    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)

    def get_doc_filename(self) -> str:
        """
        Returns the default document filename from configuration or a static setting.
        Can be overridden in subclasses to return different filenames based on the context.
        """
        return config.SR_STEP4_DOCX_FILENAME
    
    def get_mime_type(self):
        return config.DOCX_MIME
