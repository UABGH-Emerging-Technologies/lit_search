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
        self.categorize_manager = FastAPICategorizeManager()

    def categorize_articles(self):
        if self.df is not None:
            reduced_df = self.get_relevant_rows(self.df).copy()
            input_list = self.userdefined_categories.split(",")
            input_list = [value.strip() for value in input_list if value.strip()]

            for index, row in reduced_df.iterrows():
                data = row[["abstract", "title"]]
                assembled_prompt = self._assemble_prompt(thing_to_categorize=data)
                response = self.single_response.generate_response(assembled_prompt)
                self.single_response.update_total_cost()
                assigned_categories = response.content.replace("'", "")
                reduced_df.loc[index, "category"] = assigned_categories.lower()            
            try:
                full_text_df = self.categorize_manager.fetch_full_text(reduced_df['PMID'])
                category_df = pd.merge(reduced_df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df

    def get_tempfile_excel(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            self.categorize_manager.write_excel_output(
                tmpfile=tmpfile.name,
                df=category_df,
                )
        return tmpfile.name
    
    def process(self):
        category_df = self.categorize_articles()
        if category_df is not None:
            file_path = self.get_tempfile_excel(category_df)
            return file_path
        return None
