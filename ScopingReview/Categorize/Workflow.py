from aiweb_common.WorkflowHandler import WorkflowHandler
import pandas as pd
import tempfile
from ScopingReview_config import config
from ScopingReview.Categorize.Manager import 

class CategorizeWorkflow(WorkflowHandler):
    def __init__(self, df, userdefined_categories):
        super().__init__()
        self.df = df
        self.userdefined_categories = userdefined_categories

    def categorize_articles(self):
        if self.df is not None:
            category_df, response_meta = self.categorize(self.df, self.userdefined_categories)
            self._update_total_cost(response_meta)
            try:
                full_text_df = fetch_full_text(category_df['PMID'])
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
    
    #TODO MAp to new AIWEB implementation
    def categorize(self, category_df: pd.DataFrame, input_text: str) -> Tuple[pd.DataFrame, Any]:
        # using copy to stop view vs copy warning in pandas
        reduced_df = self.get_relevant_rows(category_df).copy()
        input_list = input_text.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        
        #TODO port this to LLM_Utils implementation
        for index, row in reduced_df.iterrows():
            data = row[["abstract", "title"]]
            with get_openai_callback() as response_meta:
                result = lit_config.CHAT35.invoke(
                    lit_prompts.categorization_chat_prompt.format_prompt(
                        categories=input_list, context=data
                    ).to_messages()
                )
            keyword_list = result.content.replace("'", "")
            reduced_df.loc[index, "category"] = keyword_list.lower()
        return reduced_df, response_meta

    def process(self):
        category_df = self.categorize_articles()
        if category_df is not None:
            file_path = self.save_results_to_excel(category_df)
            return file_path
        return None
