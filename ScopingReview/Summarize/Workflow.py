import os
import datetime
from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config, boilerplate
from aiweb_common.file_operations.text_format import convert_markdown_docx
from fastapi import HTTPException
from typing import Tuple, Optional

class SummarizeArticles(WorkflowHandler):
    def __init__(self, df, research_q):
        super().__init__()
        self.df = df
        self.research_q = research_q

    #TODO update 
    def check_limits(self):
        categories_exceeding_limit = summarize_all_categories.categories_limit_check(self.df)
        return categories_exceeding_limit

    def subcategorize(self, sub_categories):
        categories_exceeding_limit = self.check_limits()
        if categories_exceeding_limit:
            self.df, self.categories_str, response_meta = summarize_all_categories.sub_categorize(
                self.df, categories_exceeding_limit, sub_categories
            )
            self.df.drop_duplicates(subset="PMID", keep="first", inplace=True)
            return self.df, self.categories_str, response_meta
        return None, None, None

    def summarize_articles(self) -> Tuple[bytes, dict, Optional[str]]:
        if self.df is not None:
            markdown_to_convert, response_meta = summarize_all_categories(
                self.df, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            self._update_total_cost(response_meta)
            return docx_data
        else:
            raise HTTPException(status_code=404, detail="No data available for summarization.")

    #TODO Port this over to LLM_Utils implementation
    def summarize_all_categories(df, user_question, newsletter_flag=False):
        # use abtract when text is not available.
        df["Text"] = df.apply(
            lambda row: row["abstract"] if row["Text"] == "Text not available" else row["Text"], axis=1
        )

        # if no abstract or text, remove the article
        df.dropna(inplace=True, subset=["Text"])
        # takes in multiple categories and assigns them in each row
        df_exploded = df.explode("category")

        # get categories
        categories = df_exploded["category"].unique()

        output = []
        for current_category in categories:
            print(current_category)
            with get_openai_callback() as response_meta:
                filtered_rows = df_exploded[df_exploded["category"] == current_category]
                article_summaries = []
                for idx, row in filtered_rows.iterrows():
                    print(row.title)
                    article_summary = summarize_article_in_chunks(row.Text)
                    # TODO: nice to haves
                    # df_exploded.at[idx, 'Article Summary'] = article_summary
                    formatted_summary = (
                        f"APA Citation: {row.citation}\n\n Summary: {article_summary}\n\n --- "
                    )
                    article_summaries.append(formatted_summary)
                text_to_summarize = "\n\n".join(article_summaries)

                if newsletter_flag:
                    result = lit_config.SUMMARIZE_CHAT.invoke(
                        lit_prompts.newsletter_chat_prompt.format_prompt(
                            category=current_category, content=text_to_summarize
                        ).to_messages()
                    )

                    output.append(result.content)

                else:
                    result = lit_config.SUMMARIZE_CHAT.invoke(
                        lit_prompts.category_summary_chat_prompt.format_prompt(
                            question=user_question, category=current_category, content=text_to_summarize
                        ).to_messages()
                    )

                    output.append(
                        "# "
                        + str(current_category)
                        + "\n\n"
                        + result.content
                        + "\n\n"
                        + "\n\n".join(filtered_rows.citation)
                    )
        return "\n\n".join(output), response_meta

    def write_newsletter(self, category, output_folder, template_location=None):
        if self.df is not None:
            newsletter_body, response_meta = summarize_all_categories(
                self.df, self.research_q, newsletter_flag=True
            )
            markdown_to_convert = (
                "## "
                + category.title()
                + " AI-Generated Literature Digest \n\n"
                + boilerplate.NEWSLETTER_FRONTMATTER
                + "\n\n"
                + newsletter_body
                + "\n\n"
                + boilerplate.NEWSLETTER_BACKMATTER
            )
            docx_data = convert_markdown_docx(markdown_to_convert, template_location)
            self.save_newsletter(docx_data, category, output_folder)
            self._update_total_cost(response_meta)
            
    #TODO Rework this to use LLM utils properly  
    def summarize_article_in_chunks(article_text):
        # Splitting the article text into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=13000, chunk_overlap=1000
        )
        texts = text_splitter.create_documents([article_text])
        # Create the initial summary for the first chunk
        summary = lit_config.CHAT35.invoke(lit_prompts.initial_summary_prompt.format(text=texts[0]))

        # Iteratively refine the summary with each subsequent chunk
        
        if len(texts) > 1:
            for text_chunk in texts[1:]:
                summary = lit_config.CHAT35.invoke(
                    lit_prompts.refine_summary_prompt.format(existing_summary=summary, text=text_chunk)
                )
        return summary

    def save_newsletter(self, docx_data, category, output_folder):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        today_date = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"{category}_{today_date}.docx"
        file_path = os.path.join(output_folder, filename)

        with open(file_path, "wb") as file:
            file.write(docx_data)
        print(f"File saved: {file_path}")

    def process(self):
        docx_data = self.summarize_articles()
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None
