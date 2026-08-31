import json
import re
from collections import Counter
from typing import List

from pydantic import BaseModel, Field

from ScopingReview.BaseManager import BaseManager


class KeywordData(BaseModel):
    """Pydantic model holding the three keyword lists produced by keyword extraction."""

    primary_keywords: List[str] = Field(
        ..., example=["keyword1", "keyword2"], description="List of primary keywords"
    )
    secondary_keywords: List[str] = Field(
        ..., example=["keyword3", "keyword4"], description="List of secondary keywords"
    )
    exclusion_keywords: List[str] = Field(
        ..., example=["keyword5"], description="List of exclusion keywords"
    )


class KeywordManager(BaseManager):
    """Extracts, cleans, and formats keywords from article metadata.

    Args:
        df: DataFrame of articles with ``keywords`` and ``title`` columns.
        research_q: The research question for context.
    """

    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q

    @staticmethod
    def _extract_json_from_markdown(markdown_text):
        """Extract the first JSON object embedded in a markdown string.

        Args:
            markdown_text: Raw markdown text potentially containing JSON.

        Returns:
            Parsed dict on success, or an error-description string on failure.
        """
        # Regular expression to match JSON object within markdown
        json_pattern = re.compile(r"\{.*?\}", re.DOTALL)

        # Find JSON object in the markdown text
        match = json_pattern.search(markdown_text)

        if match:
            json_str = match.group(0)
            try:
                json_data = json.loads(json_str)  # Validate the JSON string
                return json_data
            except json.JSONDecodeError:
                return "Invalid JSON detected."
        else:
            return "No JSON object found."

    def _clean_keywords(self, keywords):
        """Strip special characters from a list of keyword strings.

        Args:
            keywords: Raw keyword strings.

        Returns:
            List of cleaned keyword strings.
        """
        cleaned_keywords = []
        for keyword in keywords:
            keyword = (
                keyword.strip()
                .replace("'", "")
                .replace("*", "")
                .replace("[", "")
                .replace("]", "")
                .replace("/", ", ")
                .replace("&", "")
            )
            cleaned_keywords.append(keyword)
        return cleaned_keywords

    def _clean_title(self, title):
        """Strip special characters from an article title.

        Args:
            title: Raw title string.

        Returns:
            Cleaned title string.
        """
        title = (
            title.strip()
            .replace("'", "")
            .replace("*", "")
            .replace("[", "")
            .replace("]", "")
            .replace("/", ", ")
            .replace("&", "and")
        )
        return title

    def format_keywords(self, relevant_rows):
        """Count keyword frequencies across relevant articles and return formatted strings.

        Args:
            relevant_rows: DataFrame filtered to relevant articles.

        Returns:
            List of strings in ``"keyword xN"`` format.
        """
        all_keywords = []
        for keywords in relevant_rows["keywords"]:
            keywords_list = [keyword.strip().lower() for keyword in keywords.split(",")]
            clean_keywords_list = self._clean_keywords(keywords_list)
            all_keywords.extend(clean_keywords_list)

        all_titles = []
        for title in relevant_rows["title"]:
            titles_list = self._clean_title(title)
            all_titles.extend(titles_list)

        keyword_counts = Counter(all_keywords)
        formatted_keywords = [f"{k} x{v}" for k, v in keyword_counts.items()]
        return formatted_keywords

    def get_unique_keywords(self):
        """Return a comma-separated string of unique keywords from relevant articles."""
        self.df["Relevant"] = self.df.apply(self._check_relevance, axis=1)
        relevant_df = self.df.dropna(subset=["Relevant"])

        all_keywords = ",".join(relevant_df["keywords"]).split(",")
        all_keywords = [keyword.strip().lower() for keyword in all_keywords]

        unique_keywords = list(set(all_keywords))
        unique_keywords_str = ", ".join(unique_keywords)

        return unique_keywords_str

    def parse_keywords(self, content):
        """Parse LLM-generated keyword JSON into three separate lists.

        Args:
            content: Raw LLM response text containing embedded JSON.

        Returns:
            Tuple of (primary_keywords, secondary_keywords, exclusion_keywords).
        """
        data = self._extract_json_from_markdown(content)
        # _extract_json_from_markdown may return a dict when successful, or a string/error message when not.
        # Defensively handle non-dict returns to avoid AttributeError/TypeError in production/tests.
        if not isinstance(data, dict):
            # Return empty lists which are safe defaults when parsing fails
            return [], [], []
        primary_keywords = data.get("Primary Keywords", [])
        secondary_keywords = data.get("Secondary Keywords", [])
        exclusion_keywords = data.get("Exclusion Keywords", [])

        return primary_keywords, secondary_keywords, exclusion_keywords
