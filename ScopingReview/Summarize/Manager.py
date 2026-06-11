import datetime
import logging
import os
import tempfile

import pandas as pd
from aiweb_common.file_operations.file_handling import convert_markdown_docx

import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager

logger = logging.getLogger(__name__)


class SummarizeManager(BaseManager):
    """Manages article summarization logistics — file naming, saving, and category limit checks.

    Args:
        df: Categorized article DataFrame.
        research_q: The research question.
    """

    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q
        self.categories = []
        self.categories_str = ""

    def get_filename(self):
        raise NotImplementedError("This method must be implemented by subclasses.")

    def get_mime_type(self):
        return config.DOCX_MIME

    def save_newsletter(self, docx_data, category, output_folder):
        """Save a newsletter DOCX to a date-stamped file in the output folder.

        Args:
            docx_data: Raw DOCX bytes.
            category: Newsletter category name (used in filename).
            output_folder: Directory path for the output file.
        """
        # Ensure the output folder exists
        # TODO Change all os.path to pathlib
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Format the filename
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"{category}_{today_date}.docx"
        file_path = os.path.join(output_folder, filename)

        # Save the document
        with open(file_path, "wb") as file:
            file.write(docx_data)
        logger.info("File saved: %s", file_path)

    @staticmethod
    def categories_limit_check(df):
        """Identify categories with more articles than the configured threshold.

        Args:
            df: DataFrame with a ``category`` column (may be comma-separated).

        Returns:
            List of category names exceeding :data:`config.SUBCLASS_THRESHOLD`.
        """
        categories_exceeding_limit = []
        if df is not None:
            df["category"] = df["category"].str.split(", ")
            df_exploded = df.explode("category")

            unique_values_counts = df_exploded["category"].value_counts()
            for category, count in unique_values_counts.items():
                if count > config.SUBCLASS_THRESHOLD:
                    categories_exceeding_limit.append(category)
        # Note that in Python, empty lists return False in boolean checks
        return categories_exceeding_limit


class FastAPISummarizeManager(SummarizeManager):
    """FastAPI-oriented summarization manager."""

    def __init__(self, df: pd.DataFrame, research_q: str):
        super().__init__(df, research_q)

    def get_doc_filename(self) -> str:
        """
        Returns the default document filename from configuration or a static setting.
        Can be overridden in subclasses to return different filenames based on the context.
        """
        return config.SR_STEP4_DOCX_FILENAME
