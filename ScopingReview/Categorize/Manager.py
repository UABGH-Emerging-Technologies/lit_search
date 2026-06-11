import tempfile
from typing import Any, Tuple

import pandas as pd
from fastapi import HTTPException  # Importing HTTPException

import ScopingReview_config.boilerplate as boilerplate
import ScopingReview_config.config as config
import ScopingReview_config.prompt_config as prompt_config
from ScopingReview.BaseManager import BaseManager


# TODO move aiweb_common stuff to Categorize.Workflow
class BaseCategorizeManager(BaseManager):
    """Manages article categorization using user-defined category labels.

    Args:
        df_to_categorize: Article DataFrame to be categorized.
        userdefined_categories: Comma-separated category labels.
    """

    def __init__(self, df_to_categorize, userdefined_categories):
        super().__init__(df_to_categorize)
        # convert comma separated values to list and store as self.categories
        input_list = userdefined_categories.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        self.categories = input_list

    def _get_filename(self):
        return config.SR_STEP3_FILENAME

    def _get_mime_type(self):
        return config.EXCEL_MIME

    def _assemble_prompt(self, thing_to_categorize):
        """Build an LLM prompt for categorizing a single article.

        Args:
            thing_to_categorize: Article data (typically abstract + title) to categorize.

        Returns:
            Assembled prompt ready for the LLM.
        """
        print("assembling prompts")
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.CATEGORIZE_SYSTEM_TEMPLATE,
            user_prompt=prompt_config.CATEGORIZE_HUMAN_TEMPLATE,
            context=thing_to_categorize,
            categories=self.categories,
        )
        return assembled_prompt

    def _extract_full_text(self):
        """Fetch full-text content for all articles and merge into the DataFrame.

        Returns:
            DataFrame with full-text ``Text`` column merged in.
        """
        if self.df is not None:
            try:
                full_text_df = self.fetch_full_text(self.df["PMID"])
                category_df = pd.merge(self.df, full_text_df, on="PMID", how="inner")
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df

    def save_results_to_excel(self, category_df):
        """Save categorized articles to a temporary Excel file.

        Args:
            category_df: DataFrame with assigned categories.

        Returns:
            Path to the temporary Excel file.
        """
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode="wb") as tmpfile:
                category_df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            raise


class FastAPICategorizeManager(BaseCategorizeManager):
    """FastAPI-oriented categorization manager."""

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
                raise HTTPException(
                    status_code=404, detail="No data to categorize or articles not found."
                )
            return self.save_results_to_excel(category_df)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# class StreamlitCategorizeManager(BaseCategorizeManager):
#     def __init__(self, df, userdefined_categories):
#         import streamlit as st
#         super().__init__(df,userdefined_categories)
#         st.session_state["file_uploaded_cate"] = False

#     def _download_results(self, category_df):
#         import streamlit as st  # Ensure streamlit is imported within the method
#         category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
#         st.write("Note that once you hit download, this form will reset.")
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
#             write_excel_output(tmpfile, category_df, self.userdefined_categories)
#             with open(tmpfile.name, "rb") as file:
#                 st.balloons()
#                 st.download_button(
#                     label=self.get_download_button_label(),
#                     data=file,
#                     file_name=self.get_filename(),
#                     mime=self._get_mime_type(),
#                 )


#     def get_download_button_label(self):
#         return config.EXCEL_DOWNLOAD_LABEL

#     def categorize_articles(self):
#         import streamlit as st  # Ensure streamlit is imported within the method
#         super().categorize_articles()
#         if self.df is not None:
#             st.session_state["file_uploaded_cate"] = True
#             with st.spinner("Categorizing contents of file..."):
#                 category_df = self.categorize_articles()
#             self._download_results(category_df)
