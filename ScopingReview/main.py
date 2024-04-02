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
    return f'({base_query}) AND ("{start_date}"[Date - Publication] : "{end_date}"[Date - Publication])'

category_queries = {
    Category.cardiac: format_query("cardiac anesthesia OR cardiac anaesthesia OR cardiac anesthesiology OR heart anesthesia OR cardiothoracic anesthesia OR cardiothoracic anesthesiology"),
    Category.OB: format_query("obstetric anesthesia OR obstetric anaesthesia OR maternal anesthesia OR perinatal anesthesia"),
    Category.regional: format_query("regional anesthesia OR regional anaesthesia OR nerve block OR spinal anesthesia OR epidural anesthesia"),
    Category.general: format_query("general anesthesia OR general anaesthesia")
}

class NewsletterManager:
    def __init__(self, scoping_step):
        self.scoping_step = scoping_step

    def manage_initial_lit_review(self, category: str, output_folder: str, template_location: Optional[str]):
        article_search_manager = NewsletterSearchManager(self.scoping_step, category)
        category_df  = article_search_manager.search_and_compile_articles(write_excel=False)
        
        if df is not None and not df.empty:
            category_df  = category_df .head(40)  # Limit due to GPT limitations
            category_df ['Author 1: Relevant Article? (Yes/No)'] = "Yes"
            category_df ['category'] = category
            full_text_df = fetch_full_text(category_df['PMID'])
            category_df = pd.merge(category_df, full_text_df, on="PMID", how="inner")

            summarize_manager = SummarizeManager(category_df, category, is_streamlit=False)

            summarize_manager.write_newsletter(category, output_folder, template_location)
            print("Newsletter generation complete.")
        else:
            print("No articles found for the category:", category)

@app.command()
def main(category: Category = typer.Argument(..., help="Category for the literature review"),
         output_folder: str = typer.Option(..., "--output", "-o", help="Output folder for the newsletter"),
         template_location: Optional[str] = typer.Option(None, "--template", "-t", help="Optional DOCX template location")):
    scoping_step = 'initial'  # Adjust as needed
    nl_manager = NewsletterManager(scoping_step)
    nl_manager.manage_initial_lit_review(category.name, output_folder, template_location)

if __name__ == "__main__":
    app()