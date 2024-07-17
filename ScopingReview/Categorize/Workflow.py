from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview.Categorize.Manager import FastAPICategorizeManager
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from typing import Tuple, Any

class CategorizeWorkflow(WorkflowHandler):
    def __init__(self, df, userdefined_categories):
        super().__init__()
        self.df = df
        self.userdefined_categories = userdefined_categories
        self.categorize_manager = CategorizeManager()

    def categorize_articles(self):
        if self.df is not None:
            category_df = self.categorize_manager.categorize_articles(self.df, self.userdefined_categories)
            try:
                full_text_df = self.categorize_manager.fetch_full_text(category_df['PMID'])
                category_df = pd.merge(category_df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df

    def save_results_to_excel(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='wb') as tmpfile:
                category_df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            raise

    def process(self):
        category_df = self.categorize_articles()
        if category_df is not None:
            file_path = self.save_results_to_excel(category_df)
            return file_path
        return None
