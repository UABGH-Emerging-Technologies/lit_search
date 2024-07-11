from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config, boilerplate
from aiweb_common.generate import summarize_all_categories, write_first_draft
from aiweb_common.file_operations.text_format import convert_markdown_docx
from ScopingReview.WorkflowSearch import write_excel_output

class SummarizeArticles(WorkflowHandler):
    def __init__(self, df, research_q):
        super().__init__()
        self.df = df
        self.research_q = research_q

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

    def summarize_articles(self):
        if self.df is not None:
            markdown_to_convert, response_meta = summarize_all_categories(
                self.df, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            self._update_total_cost(response_meta)
            return docx_data

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
