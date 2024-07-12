import os
import datetime
import pandas as pd 

import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager
import streamlit as st
from aiweb_common.file_operations.FileHandler import convert_markdown_docx
import tempfile

class SummarizeManager(BaseManager):
    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q
        self.categories = []
        self.sub_categories = ""
        self.categories_str = ""

    def get_filename(self):
        raise NotImplementedError("This method must be implemented by subclasses.")

    def get_mime_type(self):
        raise NotImplementedError("This method must be implemented by subclasses.")

    def save_newsletter(self, docx_data, category, output_folder):
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

    def download_excel_results(self, categories_str):
        self.df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            self.write_excel_output(tmpfile, self.df, categories_str)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_excel_filename(),
                    mime=self.get_mime_type(),
                )

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

    def summarize_articles(self) -> Tuple[bytes, dict, Optional[str]]:
        """
        Summarize the articles using the provided research question.
        Checks for category limits and warns if they are exceeded.
        """
        if self.df is not None:
            categories_exceeding_limit = self.check_limits()
            warning_msg = ""
            if categories_exceeding_limit:
                warning_msg = (f"Consider breaking the following categories into subcategories, "
                               f"as there are more than {config.SUBCLASS_THRESHOLD} articles in them: "
                               f"{', '.join(categories_exceeding_limit)}.")

            markdown_to_convert, response_meta = lit_generate.summarize_all_categories(
                self.df, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            return docx_data, response_meta, warning_msg
        else:
            raise HTTPException(status_code=404, detail="No data available for summarization.")

    def save_document(self, docx_data, filename=None) -> str:
        """
        Save the DOCX data to a file and return the file path.
        Allows specifying a filename or uses the default from get_doc_filename().
        """
        if filename is None:
            filename = self.get_doc_filename()
        try:
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as file:
                file.write(docx_data)
            return file_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save DOCX file: {str(e)}")

    def summarize_and_save(self) -> Tuple[str, float]:
        """
        Performs the complete summarization process and saves the result to a DOCX file,
        returning any warnings related to category limits.
        """
        docx_data, response_meta, warning_message = self.summarize_articles()
        self.cost += response_meta.total_cost
        if docx_data:
            file_path = self.save_document(docx_data)
            return file_path, warning_message
        else:
            raise HTTPException(status_code=404, detail="Failed to generate document data.")

    def standalone_summarize_and_save(self):
        """
        This method encapsulates the summarization of articles and saving the result as a DOCX file.
        It returns the path to the saved file and the total cost associated with the operation.
        """
        try:
            if self.df.empty:
                raise HTTPException(status_code=404, detail="No articles found")

            # Preparing the dataframe for summarization
            self.df = self.df.head(lit_config.SUBCLASS_THRESHOLD)
            self.df["Author 1: Relevant Article? (Yes/No)"] = "Yes"
            self.df["category"] = "Initial Search"
            self.df["Text"] = "Text not available"

            # Summarizing articles
            markdown_to_convert, response_meta = lit_generate.summarize_all_categories(self.df, self.research_q)
            self.cost += response_meta.total_cost
            docx_data = convert_markdown_docx(markdown_to_convert)

            # Save the DOCX file
            temp_file_path = self.save_document(docx_data)

            return temp_file_path, self.cost
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
