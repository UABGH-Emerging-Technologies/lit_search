import datetime
import warnings
from typing import Optional

import pandas as pd
import typer


import ScopingReview_config.config as lit_config
from ScopingReview.BaseManager import SummarizeManager
from ScopingReview.data import fetch_full_text
from ScopingReview.SearchManager import NewsletterSearchManager

# move to config

# Initialize Typer CLI app
app = typer.Typer()
warnings.filterwarnings("ignore")

app = typer.Typer()


# helper functions
def get_last_week_dates():
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=7)
    return start_date.strftime("%Y/%m/%d"), end_date.strftime("%Y/%m/%d")


def format_query(base_query):
    start_date, end_date = get_last_week_dates()
    return f'({base_query}) AND ("{start_date}"[Date - Entrez] : "{end_date}"[Date - Entrez]) AND ("{start_date}"[Date - Publication] : "{end_date}"[Date - Publication])'


# define each category query
category_queries = {
    category: format_query(query) for category, query in lit_config.NEWSLETTER_QUERIES.items()
}


class NewsletterManager:
    def __init__(self, scoping_step):
        self.scoping_step = scoping_step
        self.cost = 0.0

    def manage_newsletter(
        self, category: str, query: str, output_folder: str, template_location: Optional[str]
    ):
        # Initialize NewsletterSearchManager with the predefined query
        question = lit_config.NEWSLETTER_QUESTION.format(category=category)
        article_search_manager = NewsletterSearchManager(
            self.scoping_step, query, research_q=question
        )
        category_df = article_search_manager.search_and_compile_articles()

        if category_df is not None and not category_df.empty:
            category_df = category_df.head(40)  # Limit due to GPT limitations

            # Fetch full text, merge, and process as before
            full_text_df = fetch_full_text(category_df["PMID"])
            category_df = pd.merge(category_df, full_text_df, on="PMID", how="inner")
            category_df["Text"] = category_df["Text"].fillna("Text not available")
            category_df["Author 1: Relevant Article? (Yes/No)"] = "Yes"
            category_df["category"] = category
            summarize_manager = SummarizeManager(category_df, question, is_streamlit=False)
            response_meta = summarize_manager.write_newsletter(
                category, output_folder, template_location
            )
            print(category, "newsletter generation complete. Cost: ", response_meta.total_cost)

        else:
            print("No articles found for the category:", category)


@app.command()
def main(
    output_folder: str = typer.Option(
        ..., "--output", "-o", help="Output folder for the newsletter"
    ),
    template_location: Optional[str] = typer.Option(
        None, "--template", "-t", help="Optional DOCX template location"
    ),
):
    scoping_step = "initial"
    nl_manager = NewsletterManager(scoping_step)

    for category in lit_config.NEWSLETTER_CATEGORIES:
        query = category_queries[category]
        nl_manager.manage_newsletter(category, query, output_folder, template_location)


if __name__ == "__main__":
    app()
