import warnings
import enum
import datetime
import typer
from typing import Optional
import pandas as pd 

from ScopingReview.search import NewsletterSearchManager
from ScopingReview.compile import SummarizeManager
from ScopingReview.data import fetch_full_text

# Initialize Typer CLI app
app = typer.Typer()
warnings.filterwarnings("ignore")

app = typer.Typer()

class Category(enum.Enum):
    cardiac = "cardiac"
    OB = "OB"
    regional = "regional"
    general = "general"

def get_last_week_dates():
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=7)
    return start_date.strftime("%Y/%m/%d"), end_date.strftime("%Y/%m/%d")

def format_query(base_query):
    start_date, end_date = get_last_week_dates()
    return f'({base_query}) AND ("{start_date}"[Date - Entrez] : "{end_date}"[Date - Entrez]) AND ("{start_date}"[Date - Publication] : "{end_date}"[Date - Publication])'

category_queries = {
    Category.cardiac: format_query("cardiac anesthesia OR cardiac anaesthesia OR cardiac anesthesiology OR heart anesthesia OR cardiothoracic anesthesia OR cardiothoracic anesthesiology"),
    Category.OB: format_query("obstetric anesthesia OR obstetric anaesthesia OR maternal anesthesia OR perinatal anesthesia"),
    Category.regional: format_query("regional anesthesia OR regional anaesthesia OR nerve block OR spinal anesthesia OR epidural anesthesia"),
    Category.general: format_query("general anesthesia OR general anaesthesia")
}

 
class NewsletterManager:
    def __init__(self, scoping_step):
        self.scoping_step = scoping_step

    @profile
    def manage_newsletter(self, category: str, query: str, output_folder: str, template_location: Optional[str]):
        # Initialize NewsletterSearchManager with the predefined query
        question = "Developments in " + category + " anesthesia that may impract clinical practice"
        article_search_manager = NewsletterSearchManager(self.scoping_step, query, research_q=question)
        category_df = article_search_manager.search_and_compile_articles()

        if category_df is not None and not category_df.empty:
            category_df = category_df.head(40)  # Limit due to GPT limitations
            
            # Fetch full text, merge, and process as before
            full_text_df = fetch_full_text(category_df['PMID'])
            category_df = pd.merge(category_df, full_text_df, on="PMID", how="inner")
            category_df['Text'] = category_df['Text'].fillna("Text not available")
            category_df['Author 1: Relevant Article? (Yes/No)'] = "Yes"
            category_df['category'] = category

            summarize_manager = SummarizeManager(category_df, question, is_streamlit=False)
            summarize_manager.write_newsletter(category, output_folder, template_location)
            print("Newsletter generation complete.")
        else:
            print("No articles found for the category:", category)


@app.command()
def main(category: Category = typer.Argument(..., help="Category for the literature review"),
         output_folder: str = typer.Option(..., "--output", "-o", help="Output folder for the newsletter"),
         template_location: Optional[str] = typer.Option(None, "--template", "-t", help="Optional DOCX template location")):
    scoping_step = 'initial' # for compatability with functions that also work in st context
    query = category_queries[category]
    nl_manager = NewsletterManager(scoping_step)
    nl_manager.manage_newsletter(category.name, query, output_folder, template_location)

if __name__ == "__main__":
    app()
