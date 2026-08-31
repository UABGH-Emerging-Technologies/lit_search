import pandas as pd

import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager


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


class FastAPICategorizeManager(BaseCategorizeManager):
    """FastAPI-oriented categorization manager."""

    def __init__(self, df: pd.DataFrame, userdefined_categories: str):
        super().__init__(df, userdefined_categories)
