from pydantic import BaseModel, Field
from typing import List
from ScopingReview.BaseManager import BaseManager
import json
from collections import Counter


class KeywordsData(BaseModel):
    primary_keywords: List[str] = Field(..., example=["keyword1", "keyword2"], description="List of primary keywords")
    secondary_keywords: List[str] = Field(..., example=["keyword3", "keyword4"], description="List of secondary keywords")
    exclusion_keywords: List[str] = Field(..., example=["keyword5"], description="List of exclusion keywords")


class KeywordsManager(BaseManager):
    #TODO What else needs to go into Keywords Manager init?
    def __init__(self, df, research_q):
        super().__init__(df)
    
    def _clean_keywords(self, keywords):
        cleaned_keywords = []
        for keyword in keywords:
            # Remove surrounding single quotes and extra whitespace
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
        all_keywords = []
        for keywords in relevant_rows["keywords"]:
            keywords_list = [keyword.strip().lower() for keyword in keywords.split(",")]
            clean_keywords_list = self._clean_keywords(keywords_list)
            all_keywords.extend(clean_keywords_list)  # Use extend to flatten the list

        all_titles = []
        for title in relevant_rows["title"]:
            titles_list = self._clean_title(title)
            all_titles.extend(titles_list)  # Assuming you need to flatten this list too

        # Count occurrences of each keyword and format them
        keyword_counts = Counter(all_keywords)
        formatted_keywords = [f"{k} x{v}" for k, v in keyword_counts.items()]
        return formatted_keywords

    def get_unique_keywords(self):
        # TODO fix issue regarding warning here:
        #  A value is trying to be set on a copy of a slice from a DataFrame.
        # Try using .loc[row_indexer,col_indexer] = value instead
        self.df["Relevant"] = self.df.apply(self._check_relevance, axis=1)
        relevant_df = self.df.dropna(subset=["Relevant"])

        # Join all keywords into a single string, then split by comma
        all_keywords = ",".join(relevant_df["keywords"]).split(",")

        # Remove leading/trailing white spaces and convert to lower case
        all_keywords = [keyword.strip().lower() for keyword in all_keywords]

        # Get unique keywords
        unique_keywords = list(set(all_keywords))
        # Convert list of unique keywords to a comma-separated string
        unique_keywords_str = ", ".join(unique_keywords)

        return unique_keywords_str
    
    def parse_keywords(self, content):
        # Load the JSON string into a Python dictionary
        data = json.loads(content)

        # Extract keyword lists into variables
        primary_keywords = data.get("Primary Keywords", [])
        secondary_keywords = data.get("Secondary Keywords", [])
        exclusion_keywords = data.get("Exclusion Keywords", [])

        return primary_keywords, secondary_keywords, exclusion_keywords
