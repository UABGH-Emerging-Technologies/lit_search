import os
import datetime
import pandas as pd 
from typing import Tuple, Optional
import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager
import streamlit as st
from aiweb_common.file_operations.file_handling import convert_markdown_docx
from aiweb_common.generate.SingleResponse import SingleResponseHandler
import ScopingReview_config.prompt_config as prompt_config
import tempfile

class SummarizeManager(BaseManager):
    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q
        self.categories = []
        self.categories_str = ""
        self.fast_single_response = SingleResponseHandler(config.FAST_LLM_INTERFACE)
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)

    def get_filename(self):
        raise NotImplementedError("This method must be implemented by subclasses.")

    def get_mime_type(self):
        raise NotImplementedError("This method must be implemented by subclasses.")
    
    def assemble_initial_summary_prompt(self, first_chunk):
        print('assembling prompts')
        assembled_prompt = self.fast_single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.summarize_single_article_system_prompt, 
            user_prompt = prompt_config.initial_summary_prompt, 
            text = first_chunk
        )
        return assembled_prompt
    
    def assemble_next_summary_prompt(self, current_summary, next_chunk):
        print('assembling prompts')
        assembled_prompt = self.fast_single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.summarize_single_article_system_prompt, 
            user_prompt = prompt_config.refine_summary_prompt, 
            existing_summary = current_summary,
            test = next_chunk
        )
        return assembled_prompt
    
    def assemble_category_summary_prompt(self, articles_category, articles_summaries):
        print('assembling prompts')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SUMMARIZE_CATEGORY_TEMPLATE, 
            user_prompt = prompt_config.SUMMARIZE_HUMAN_TEMPLATE, 
            question = self.research_q,
            category = articles_category,
            content = articles_summaries
        )
        return assembled_prompt
    
    def assemble_newsletter_prompt(self, anes_category, articles_summaries):
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SUMMARIZE_NEWSLETTER_TEMPLATE, 
            user_prompt = prompt_config.SUMMARIZE_HUMAN_TEMPLATE, 
            category = anes_category,
            content = articles_summaries
        )
        return assembled_prompt

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
       
    @staticmethod 
    def categories_limit_check(df):
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

