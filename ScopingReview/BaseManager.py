import datetime
import os
import tempfile

import pandas as pd
from aiweb_common.file_operations.text_format import convert_markdown_docx

import ScopingReview.generate as lit_generate
import ScopingReview_config.boilerplate as lit_boilerplate
import ScopingReview_config.config as lit_config
import streamlit as st
from ScopingReview.data import (
    extract_docx_pmids,
    fetch_full_text,
    write_excel_output,
)
from fastapi import HTTPException
from typing import Tuple, Optional

#TODO make sure this is all ported to workflow handler
class BaseManager():
    def __init__(self, df):
        self.df = df

    def get_filename(self):
        # default implementation, subclasses MUST override this method
        raise NotImplementedError

    def get_mime_type(self):
        # default implementation, subclasses MUST override this method
        raise NotImplementedError


class BaseCategorizeManager(CompileManager):
    def __init__(self, df, userdefined_categories):
        super().__init__(df)
        self.userdefined_categories = userdefined_categories

    def get_mime_type(self):
        return lit_config.EXCEL_MIME
    
    def get_filename(self):
        return lit_config.SR_STEP3_FILENAME
    
    def categorize_articles(self):
        if self.df is not None:
            category_df, response_meta = lit_generate.categorize(self.df, self.userdefined_categories)
            self.cost += response_meta.total_cost
            try:
                full_text_df = fetch_full_text(category_df['PMID'])
                category_df = pd.merge(category_df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df

    def save_results_to_excel(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='wb') as tmpfile:
                category_df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            raise

# TODO: Refactor as StreamlitCategorizeManager
class CategorizeManager(BaseCategorizeManager):
    def __init__(self, df, userdefined_categories):
        super().__init__(df, userdefined_categories)
        st.session_state["file_uploaded_cate"] = False

    def get_download_button_label(self):
        return lit_config.EXCEL_DOWNLOAD_LABEL

    def categorize_articles(self):
        super().categorize_articles()
        if self.df is not None:
            st.session_state["file_uploaded_cate"] = True
            with st.spinner("Categorizing contents of file..."):
                category_df = self.categorize_articles()
            self._download_results(category_df)

    def _download_results(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            write_excel_output(tmpfile, category_df, self.userdefined_categories)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_filename(),
                    mime=self.get_mime_type(),
                )


class FastAPICategorizeManager(BaseCategorizeManager):
    def __init__(self, df: pd.DataFrame, userdefined_categories: str):
        super().__init__(df, userdefined_categories)

    def categorize_articles_and_save(self) -> str:
        """
        Perform the categorization and save the results to an Excel file.
        Returns the path to the Excel file.
        """
        try:
            category_df = self.categorize_articles()
            if category_df.empty:
                raise HTTPException(status_code=404, detail="No data to categorize or articles not found.")
            return self.save_results_to_excel(category_df)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def save_results_to_excel(self, category_df: pd.DataFrame) -> str:
        """
        Save the categorized DataFrame to an Excel file and return the file path.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='w+b') as tmpfile:
                write_excel_output(tmpfile, category_df, self.userdefined_categories)
                return tmpfile.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


class SummarizeManager(CompileManager):
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

    def check_limits(self):
        categories_exceeding_limit = lit_generate.categories_limit_check(self.df)
        return categories_exceeding_limit

    def subcategorize(self, sub_categories):
        categories_exceeding_limit = self.check_limits()
        if categories_exceeding_limit:
            self.df, self.categories_str, response_meta = lit_generate.sub_categorize(
                self.df, categories_exceeding_limit, sub_categories
            )
            self.df.drop_duplicates(subset="PMID", keep="first", inplace=True)
            return self.df, self.categories_str, response_meta
        return None, None, None

    def summarize_articles(self):
        if self.df is not None:
            markdown_to_convert, response_meta = lit_generate.summarize_all_categories(
                self.df, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            self.cost += response_meta.total_cost
            return docx_data, response_meta

    def write_newsletter(self, category, output_folder, template_location=None):
        if self.df is not None:
            newsletter_body, response_meta = lit_generate.summarize_all_categories(
                self.df, self.research_q, newsletter_flag=True
            )
            markdown_to_convert = (
                "## "
                + category.title()
                + " AI-Generated Literature Digest \n\n"
                + lit_boilerplate.NEWSLETTER_FRONTMATTER
                + "\n\n"
                + newsletter_body
                + "\n\n"
                + lit_boilerplate.NEWSLETTER_BACKMATTER
            )
            docx_data = convert_markdown_docx(markdown_to_convert, template_location)
            self.save_newsletter(docx_data, category, output_folder)
            return response_meta

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
        return lit_config.SR_STEP4_DOCX_FILENAME

    def get_excel_filename(self):
        return lit_config.SR_STEP4_EXCEL_FILENAME

    def get_download_button_label(self):
        return lit_config.BOTH_FILES

    def get_mime_type(self):
        return lit_config.DOCX_MIME

    def download_excel_results(self, categories_str):
        self.df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            write_excel_output(tmpfile, self.df, categories_str)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_excel_filename(),
                    mime=self.get_mime_type(),
                )
        self.update_session_cost()

    def download_doc_results(self, docx_data):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_doc_filename(),
            mime=self.get_mime_type(),
        )
        self.update_session_cost()

    def update_session_cost(self):
        if "cost" not in st.session_state:
            st.session_state["total_cost"] = self.cost
        else:
            st.session_state["total_cost"] += self.cost

    def subcategorize(self, sub_categories):
        result = super().subcategorize(sub_categories)
        if result[0] is not None:  # Check if categorization was successful
            self.update_session_cost()
        return result

    def summarize_articles(self):
        docx_data, response_meta = super().summarize_articles()
        if docx_data is not None:
            self.cost += response_meta.total_cost
            return docx_data
        return None
    
    
class FastAPISummarizeManager(SummarizeManager):
    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)

    def get_doc_filename(self) -> str:
        """
        Returns the default document filename from configuration or a static setting.
        Can be overridden in subclasses to return different filenames based on the context.
        """
        return lit_config.SR_STEP4_DOCX_FILENAME
    
    def get_mime_type(self):
        return lit_config.DOCX_MIME

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
                               f"as there are more than {lit_config.SUBCLASS_THRESHOLD} articles in them: "
                               f"{', '.join(categories_exceeding_limit)}.")

            markdown_to_convert, response_meta = lit_generate.summarize_all_categories(
                self.df, self.research_q
            )
            self.cost += response_meta.total_cost
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


# class DraftReviewManager(CompileManager):
#     def __init__(self, summaries, research_q):
#         super().__init__(None)  # Assuming the base class does not necessarily need a DataFrame
#         self.research_q = research_q
#         self.summaries = summaries

#     def get_filename(self) -> str:
#         return lit_config.SR_STEP5_FILENAME

#     def get_mime_type(self) -> str:
#         return lit_config.DOCX_MIME

#     def draft_review(self) -> bytes:
#         """
#         Generates a first draft of the document based on summaries and a research question.
#         Returns the binary data of the DOCX file.
#         """
#         if self.summaries is not None:
#             markdown_to_convert, response_meta = lit_generate.write_first_draft(
#                 self.summaries, self.research_q
#             )
#             self.cost += response_meta.total_cost
#             docx_data = convert_markdown_docx(markdown_to_convert)
#             return docx_data
#         else:
#             raise ValueError("Summaries data is required for drafting.")

#     def save_draft_review(self, docx_data: bytes) -> str:
#         """
#         Saves the generated draft review to a DOCX file and returns the file path.
#         """
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
#                 tmpfile.write(docx_data)
#                 return tmpfile.name
#         except Exception as e:
#             raise IOError(f"Failed to save draft review document: {str(e)}")


# class StreamlitDraftReviewManager(DraftReviewManager):
#     def __init__(self, summaries, research_q):
#         super().__init__(summaries, research_q)
#         st.session_state["file_uploaded_draft"] = False  # Unique file_uploaded variable for drafting

#     def _download_results(self, docx_data):
#         st.balloons()
#         st.write("Note that once you hit download, this form will reset.")
#         st.download_button(
#             label=self.get_download_button_label(),
#             data=docx_data,
#             file_name=self.get_filename(),
#             mime=self.get_mime_type(),
#         )

#     def draft_review(self):
#         docx_data = super().draft_review()
#         if docx_data:
#             self._download_results(docx_data)
#             st.session_state["file_uploaded_draft"] = True


# class FastAPIDraftReviewManager(DraftReviewManager):
#     def __init__(self, summaries, research_q):
#         super().__init__(summaries, research_q)

#     def draft_review(self) -> bytes:
#         """
#         Asynchronously generate a first draft of the document based on summaries and a research question.
#         Returns the binary data of the DOCX file.
#         Overrides the base method to include proper error handling in an asynchronous context.
#         """
#         if not self.summaries:
#             raise HTTPException(status_code=400, detail="Summaries data is required for drafting.")
        
#         try:
#             markdown_to_convert, response_meta = lit_generate.write_first_draft(
#                 self.summaries, self.research_q
#             )
#             self.cost += response_meta.total_cost
#             docx_data = convert_markdown_docx(markdown_to_convert)
#             return docx_data
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Failed to generate draft: {str(e)}")

#     def save_draft_review(self, docx_data: bytes) -> str:
#         """
#         Asynchronously save the generated draft review to a DOCX file and return the file path.
#         """
#         try:
#             temp_dir = tempfile.mkdtemp()
#             file_path = os.path.join(temp_dir, self.get_filename())
#             with open(file_path, "wb") as file:
#                 file.write(docx_data)
#             return file_path
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Failed to save draft review document: {str(e)}")


# class BibtexManager(CompileManager):
#     def __init__(self, file_contents, file_ext):
#         super().__init__(file_contents)
#         if file_contents is not None:
#             self.df = file_contents
#         self.file_ext = file_ext

#     def _get_PMID_list(self):
#         if self.file_ext == ".xlsx":
#             if "PMID" in self.df.columns:
#                 return self.df["PMID"].astype(str).tolist()
#             else:
#                 raise ValueError("PMIDs missing.")
#         elif self.file_ext == ".docx":
#             df = extract_docx_pmids(self.df)
#             if "PMID" in df.columns:
#                 return df["PMID"].astype(str).tolist()
#             else:
#                 raise ValueError("Bibliography not in expected format.")

#     def get_filename(self):
#         return lit_config.SR_STEP6_FILENAME

#     def convert_pmid_to_bibtex(self):
#         pmid_list = self._get_PMID_list()
#         if not pmid_list:
#             raise ValueError("No PMIDs found to convert to BibTeX.")
#         bibtex_text = pmid2bibtex(pmid_list)
#         return bibtex_text


# class StreamlitBibtexManager(BibtexManager):
#     def __init__(self, df, file_ext):
#         super().__init__(df, file_ext)
#         st.session_state["file_uploaded_bibtex"] = False  # Unique file_uploaded variable for bibtex management
    
#     def get_download_button_label(self):
#         return config.DOCX_DOWNLOAD_LABEL
    
#     def _download_results(self, bibtex_text):
#         st.balloons()
#         st.write("Note that once you hit download, this form will reset.")
#         st.download_button(
#             label=self.get_download_button_label(),
#             data=bibtex_text,
#             file_name=self.get_filename(),
#             mime="text/plain",
#         )
#         st.write("Thanks for playing! Please email feedback to rmelvin@uabmc.edu")


# class FastAPIBibtexManager(BibtexManager):
#     def __init__(self, content: Union[pd.DataFrame, str], file_ext: str) -> Response:
#         super().__init__(content, file_ext)

#     def convert_and_download_bibtex(self):
#         """
#         Asynchronously converts PMIDs to BibTeX format and prepares it for download.
#         Raises HTTPException if no PMIDs are found or if the BibTeX conversion fails.
#         """
#         try:
#             pmid_list = self._get_PMID_list()
#             if not pmid_list:
#                 raise ValueError("No PMIDs found to convert to BibTeX.")

#             bibtex_text = pmid2bibtex(pmid_list)
#         except ValueError as e:
#             raise HTTPException(status_code=422, detail=str(e))
            
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".bib", mode='w', encoding='utf-8') as tmpfile:
#                 tmpfile.write(bibtex_text)
#                 tmpfile_name = tmpfile.name
#             return tmpfile_name

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"An error occurred while converting PMIDs to BibTeX: {str(e)}")