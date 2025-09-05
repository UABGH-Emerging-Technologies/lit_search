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
from ScopingReview.utils import pmid2bibtex


class CompileManager:
    def __init__(self, df):
        self.df = df

    def get_filename(self):
        # default implementation, subclasses MUST override this method
        pass

    def get_mime_type(self):
        # default implementation, subclasses MUST override this method
        pass


class CategorizeManager(CompileManager):
    def __init__(self, df, userdefined_categories):
        super().__init__(df)
        self.userdefined_categories = userdefined_categories
        st.session_state[
            "file_uploaded_cate"
        ] = False  # Initiate a unique file_uploaded variable for categorization

    def get_mime_type(self):
        return lit_config.EXCEL_MIME

    def get_filename(self):
        # default implementation, subclasses can override this method
        return lit_config.SR_STEP3_FILENAME

    def get_download_button_label(self):
        return lit_config.EXCEL_DOWNLOAD_LABEL

    def categorize_articles(self):
        if self.df is not None:
            st.session_state[
                "file_uploaded_cate"
            ] = True  # file is uploaded and ready to categorize
            with st.spinner("Categorizing contents of file..."):
                category_df, response_meta = lit_generate.categorize(
                    self.df, self.userdefined_categories
                )
            st.session_state["total_cost"] += response_meta.total_cost
            with st.spinner("Getting full text"):
                full_text_df = fetch_full_text(category_df.PMID)
                category_df = pd.merge(category_df, full_text_df, on="PMID", how="inner")

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


class SummarizeManager(CompileManager):
    def __init__(self, df, research_q, is_streamlit=True):
        super().__init__(df)

        self.research_q = research_q
        self.is_streamlit = is_streamlit
        self.categories = []
        self.sub_categories = ""
        self.categories_str = ""
        if self.is_streamlit:
            st.session_state[
                "file_uploaded_sum"
            ] = False  # Initiate a unique file_uploaded variable for summarization

    def get_doc_filename(self):
        return lit_config.SR_STEP4_DOCX_FILENAME

    def get_excel_filename(self):
        return lit_config.SR_STEP4_EXCEL_FILENAME

    def get_download_button_label(self):
        return lit_config.BOTH_FILES

    def get_mime_type(self):
        return lit_config.DOCX_MIME

    # TODO add write and second sheet + Generalize and move to parent
    def _download_excel_results(self, categories_str):
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
                    mime=lit_config.EXCEL_MIME,
                )

    def _download_doc_results(self, docx_data):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_doc_filename(),
            mime=self.get_mime_type(),
        )

    def check_limits(self):
        categories_exceeding_limit = lit_generate.categories_limit_check(self.df)
        return categories_exceeding_limit

    def subcategorize(self):
        categories_exceeding_limit = self.check_limits()
        # perfoming categorization on the exceeding limit categories
        if categories_exceeding_limit:
            st.session_state["limit_exceeded"] = True
            categories_string = ", ".join(categories_exceeding_limit)
            text_box_str = (
                "More than "
                + str(lit_config.SUBCLASS_THRESHOLD)
                + " articles belong to the following category(ies). Suggest sub-categories for the following main category(ies), and separate them by commas: "
            )
            sub_categories = st.text_area(text_box_str, categories_string)
            if st.button("Subcategorize Topics"):
                with st.spinner("Subcategorization in progress"):
                    self.df, self.categories_str, response_meta = lit_generate.sub_categorize(
                        self.df, categories_exceeding_limit, sub_categories
                    )
                    self.df.drop_duplicates(subset="PMID", keep="first", inplace=True)
                    self._download_excel_results(",".split(self.categories_str))
                    st.session_state["subcategorize_complete"] = True
                st.session_state["total_cost"] += response_meta.total_cost
                st.write("You must download and review the Excel file before continuing.")
        else:
            st.write("No single category exceeded limit - ", lit_config.SUBCLASS_THRESHOLD)
            st.session_state["subcategorize_complete"] = True

    def summarize_articles(self):
        if self.df is not None:
            # file is uploaded and ready to categorize

            with st.spinner("Summarizing..."):
                markdown_to_convert, response_meta = lit_generate.summarize_all_categories(
                    self.df, self.research_q
                )
                docx_data = convert_markdown_docx(markdown_to_convert)
            st.session_state["total_cost"] += response_meta.total_cost
            self._download_doc_results(docx_data)

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


class DraftReviewManager(CompileManager):
    def __init__(self, summaries, research_q):
        super().__init__(None)
        self.research_q = research_q
        self.summaries = summaries
        st.session_state[
            "file_uploaded_draft"
        ] = False  # Initiate a unique file_uploaded variable for drafting

    def get_filename(self):
        return lit_config.SR_STEP5_FILENAME

    def get_download_button_label(self):
        return lit_config.DOCX_DOWNLOAD_LABEL

    def _download_results(self, docx_data):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=docx_data,
            file_name=self.get_filename(),
            mime=lit_config.DOCX_MIME,  # correct MIME type for docx
        )

    def draft_review(self):
        if self.summaries is not None:
            st.session_state["file_uploaded_draft"] = True  # file is uploaded and ready to draft
            with st.spinner("Preparing first draft of article..."):
                markdown_to_convert, response_meta = lit_generate.write_first_draft(
                    self.summaries, self.research_q
                )
                st.session_state["total_cost"] += response_meta.total_cost
                docx_data = convert_markdown_docx(markdown_to_convert)
                self._download_results(docx_data)


class BibtexManager(CompileManager):
    def __init__(self, df, file_ext):
        if df is not None:
            self.df = df
            self.file_ext = file_ext

    def _get_PMID_list(self):
        if self.file_ext == ".xlsx":
            if "PMID" in self.df.columns:
                return self.df["PMID"].astype(str).tolist()
            else:
                return "The dataframe doesn't contain a 'PMID' column."
        if self.file_ext == ".docx":
            df = extract_docx_pmids(self.df)
            if "PMID" in df.columns:
                return df["PMID"].astype(str).tolist()
            else:
                return "The dataframe doesn't contain a 'PMID' column."

    def get_filename(self):
        return lit_config.SR_STEP6_FILENAME

    def get_download_button_label(self):
        return lit_config.BIB_DOWNLOAD_LABEL

    def _download_results(self, bibtex_text):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(), data=bibtex_text, file_name=self.get_filename()
        )

    def convert_pmid_to_bibtex(self):
        pmid_list = self._get_PMID_list()
        bibtex_text = pmid2bibtex(pmid_list)
        self._download_results(bibtex_text)

        st.write("Thanks for playing! Please email feedback to rmelvin@uabmc.edu")
        return True
