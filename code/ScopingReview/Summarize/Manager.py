import logging

import ScopingReview_config.config as config
from ScopingReview.BaseManager import BaseManager

logger = logging.getLogger(__name__)


class SummarizeManager(BaseManager):
    """Manages article summarization logistics — file naming and category limit checks.

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
