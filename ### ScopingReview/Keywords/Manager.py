from pydantic import BaseModel, Field
from typing import List
from ScopingReview.BaseManager import BaseManager
import json
from collections import Counter
import pandas as pd

class KeywordData(BaseModel):
    primary_keywords: List[str] = Field(..., example=["keyword1", "keyword2"], description="List of primary keywords")
    secondary_keywords: List[str] = Field(..., example=["keyword3", "keyword4"], description="List of secondary keywords")
    exclusion_keywords: List[str] = Field(..., example=["keyword5"], description="List of exclusion keywords")

class KeywordManager(BaseManager):
    def __init__(self, df, research_q):
        super().__init__(df)
        self.research_q = research_q

    def _clean_keywords(self, keywords):
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
            all_keywords.extend(clean_keywords_list)

        all_titles = []
        for title in relevant_rows["title"]:
            titles_list = self._clean_title(title)
            all_titles.extend(titles_list)

        keyword_counts = Counter(all_keywords)
        formatted_keywords = [f"{k} x{v}" for k, v in keyword_counts.items()]
        return formatted_keywords

    def get_unique_keywords(self):
        self.df["Relevant"] = self.df.apply(self._check_relevance, axis=1)
        relevant_df = self.df.dropna(subset=["Relevant"])

        all_keywords = ",".join(relevant_df["keywords"]).split(",")
        all_keywords = [keyword.strip().lower() for keyword in all_keywords]

        unique_keywords = list(set(all_keywords))
        unique_keywords_str = ", ".join(unique_keywords)

        return unique_keywords_str
    
    def parse_keywords(self, content):
        data = json.loads(content)
        primary_keywords = data.get("Primary Keywords", [])
        secondary_keywords = data.get("Secondary Keywords", [])
        exclusion_keywords = data.get("Exclusion Keywords", [])

        return primary_keywords, secondary_keywords, exclusion_keywords
            
    def write_keywords_excel_output(self, tmpfile, df, unique_keywords_str):
        with pd.ExcelWriter(tmpfile.name, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            df_keywords = pd.DataFrame([unique_keywords_str], columns=['Unique Keywords'])
            df_keywords.to_excel(writer, index=False, sheet_name='Sheet2')

            workbook  = writer.book
            worksheet1 = writer.sheets['Sheet1']
            worksheet2 = writer.sheets['Sheet2']
            wrap_format = workbook.add_format({'text_wrap': True})

            for idx, col in enumerate(df.columns):
                column_len = df[col].astype(str).map(len).max()
                column_title_len = len(col)
                max_len = min(100,max(column_len, column_title_len))
                worksheet1.set_column(idx, idx, max_len + 1, wrap_format)
        
            worksheet2.set_column(0, 0, len('Unique Keywords') + 1, wrap_format)
