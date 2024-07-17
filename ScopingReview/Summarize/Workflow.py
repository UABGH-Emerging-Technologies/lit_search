import os
import datetime
from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
import ScopingReview_config.prompt_config as prompt_config
from ScopingReview_config import config, boilerplate
from aiweb_common.file_operations.text_format import convert_markdown_docx
from fastapi import HTTPException
from typing import Tuple, Optional
from ScopingReview.Summarize.Manager import SummarizeManager
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SummarizeArticles(WorkflowHandler):
    def __init__(self, df, research_q):
        super().__init__()
        self.df = df
        self.research_q = research_q
        self.summarizer = SummarizeManager(df, research_q)
        self.fast_single_response = SingleResponseHandler(config.FAST_LLM_INTERFACE)
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)
        
    def assemble_initial_summary_prompt(self, first_chunk):
        print('assembling prompts')
        assembled_prompt = self.fast_single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.summarize_single_article_system_prompt, 
            user_prompt = prompt_config.initial_summary_prompt, 
            text = first_chunk
        )
        return assembled_prompt
    
    def assemble_next_summary_prompt(self, current_summary, next_chunk):
        print('assembling prompts')
        assembled_prompt = self.fast_single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.summarize_single_article_system_prompt, 
            user_prompt = prompt_config.refine_summary_prompt, 
            existing_summary = current_summary,
            test = next_chunk
        )
        return assembled_prompt
    
    def assemble_category_summary_prompt(self, articles_category, articles_summaries):
        print('assembling prompts')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SUMMARIZE_CATEGORY_TEMPLATE, 
            user_prompt = prompt_config.SUMMARIZE_HUMAN_TEMPLATE, 
            question = self.research_q,
            category = articles_category,
            content = articles_summaries
        )
        return assembled_prompt
    
    def assemble_newsletter_prompt(self, anes_category, articles_summaries):
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SUMMARIZE_NEWSLETTER_TEMPLATE, 
            user_prompt = prompt_config.SUMMARIZE_HUMAN_TEMPLATE, 
            category = anes_category,
            content = articles_summaries
        )
        return assembled_prompt
      
    # TODO: Could be a generic llm_utils summarizer  
    def summarize_article_in_chunks(self, article_text):
        # Splitting the article text into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=13000, chunk_overlap=1000
        )
        texts = text_splitter.create_documents([article_text])
        # Create the initial summary for the first chunk
        first_summary_prompt = self.assemble_initial_summary_prompt(first_chunk=texts[0])
        summary, first_response_meta = self.fast_single_response.generate_response(first_summary_prompt)
        self._update_total_cost(first_response_meta)
        
        # Iteratively refine the summary with each subsequent chunk
        if len(texts) > 1:
            for text_chunk in texts[1:]:
                next_summary_prompt = self.assemble_next_summary_prompt(current_summary=summary.content, next_chunk=text_chunk)
                summary, next_response_meta = self.fast_single_response.generate_response(next_summary_prompt)
                self._update_total_cost(next_response_meta)

        return summary.content
        
    # TODO: Can some of this be moved into a manager method?
    def summarize_all_categories(self, newsletter_flag=False):
        # use abtract when text is not available.
        self.df["Text"] = self.df.apply(
            lambda row: row["abstract"] if row["Text"] == "Text not available" else row["Text"], axis=1
        )

        # if no abstract or text, remove the article
        self.df.dropna(inplace=True, subset=["Text"])
        # takes in multiple categories and assigns them in each row
        df_exploded = self.df.explode("category")

        # get categories
        categories = df_exploded["category"].unique()

        output = []
        for current_category in categories:
            print(current_category)
            filtered_rows = df_exploded[df_exploded["category"] == current_category]
            article_summaries = []
            for _, row in filtered_rows.iterrows():
                print(row.title)
                article_summary = self.summarize_article_in_chunks(row.Text)
                # TODO: nice to haves
                # df_exploded.at[idx, 'Article Summary'] = article_summary
                formatted_summary = (
                    f"APA Citation: {row.citation}\n\n Summary: {article_summary}\n\n --- "
                )
                article_summaries.append(formatted_summary)
            text_to_summarize = "\n\n".join(article_summaries)

            if newsletter_flag:
                newsletter_prompt = self.assemble_newsletter_prompt(
                    anes_category=current_category,
                    articles_summaries=text_to_summarize
                    )
                response, response_meta = self.single_response.generate_response(newsletter_prompt)
                self._update_total_cost(response_meta)

                output.append(response.content)

            else:
                category_summary_prompt = self.assemble_category_summary_prompt(
                    current_category, text_to_summarize
                )
                response, response_meta = self.single_response.generate_response(category_summary_prompt)
                self._update_total_cost(response_meta)

                output.append(
                    "# "
                    + str(current_category)
                    + "\n\n"
                    + response.content
                    + "\n\n"
                    + "\n\n".join(filtered_rows.citation)
                )
        return "\n\n".join(output)

    def summarize_articles(self) -> Tuple[bytes, dict, Optional[str]]:
        if self.df is not None:
            categories_exceeding_limit = self.summarizer.categories_limit_check(self.df)
            warning_msg = ""
            if categories_exceeding_limit:
                warning_msg = (f"Consider breaking the following categories into subcategories, "
                               f"as there are more than {config.SUBCLASS_THRESHOLD} articles in them: "
                               f"{', '.join(categories_exceeding_limit)}.")

            markdown_to_convert = self.summarize_all_categories()
            
            return markdown_to_convert, warning_msg
        else:
            raise HTTPException(status_code=404, detail="No data available for summarization.")

    def write_newsletter(self, category, output_folder, template_location=None):
        if self.df is not None:
            newsletter_body = self.summarize_all_categories(
                newsletter_flag=True
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
        md_output, warning_msg = self.summarize_articles()
        return md_output, warning_msg
