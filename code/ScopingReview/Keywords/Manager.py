import json
import logging
import re
from collections import Counter
from typing import List

from pydantic import BaseModel, Field

from ScopingReview.BaseManager import BaseManager

logger = logging.getLogger(__name__)


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
        if not isinstance(markdown_text, str):
            return "No JSON object found."

        # Prefer an explicit ```json fenced block when the model emits one.
        fenced = re.search(r"```(?:json)?\s*(.+?)```", markdown_text, re.DOTALL)
        candidates = [fenced.group(1)] if fenced else []

        # Otherwise take the first balanced {...} span. A non-greedy \{.*?\}
        # stops at the first closing brace, which truncates any nested object
        # and yields "Invalid JSON detected." -> silently empty keyword lists.
        start = markdown_text.find("{")
        if start != -1:
            depth = 0
            in_string = False
            escaped = False
            for i in range(start, len(markdown_text)):
                ch = markdown_text[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    continue
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        candidates.append(markdown_text[start:end])
                        break

        for candidate in candidates:
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue
        return "Invalid JSON detected." if candidates else "No JSON object found."

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
            logger.warning(
                "Keyword extraction could not parse JSON from the model response (%s); "
                "continuing with no keywords, which disables keyword filtering downstream.",
                data,
            )
            return [], [], []

        # Match key names loosely. The model is asked for "Primary Keywords" but
        # readily answers with primary_keywords / primaryKeywords / PRIMARY.
        # An exact-match lookup turns any of those into silently empty lists.
        normalized = {re.sub(r"[^a-z]", "", str(k).lower()): v for k, v in data.items()}

        def pick(name: str) -> list:
            value = normalized.get(name, [])
            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]
            return value if isinstance(value, list) else []

        primary_keywords = pick("primarykeywords")
        secondary_keywords = pick("secondarykeywords")
        exclusion_keywords = pick("exclusionkeywords")

        if not (primary_keywords or secondary_keywords or exclusion_keywords):
            logger.warning(
                "Keyword extraction returned no keywords at all. Parsed JSON keys were %s; "
                "expected primary/secondary/exclusion keyword lists. The refined search will "
                "run without keyword filtering.",
                sorted(data.keys()),
            )

        return primary_keywords, secondary_keywords, exclusion_keywords
