import ScopingReview.data as review_data
import ScopingReview_config.prompt_config as prompt_config
import ScopingReview_config.boilerplate as boilerplate
import ScopingReview_config.config as config
import pandas as pd
import tempfile
from typing import Tuple, Any
from abc import abstractmethod

from llm_utils import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler

#TODO capture categorizing specific behavior in generate

class BaseCategorizeManager(WorkflowHandler):
    def __init__(self, df_to_categorize, userdefined_categories):
        super().__init__()
        self.df_to_categorize = df_to_categorize
        # convert comma separated values to list and store as self.categories
        input_list = userdefined_categories.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        self.categories = input_list
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)

    @abstractmethod      
    def _get_filename(self):
        raise NotImplementedError   
    
    @abstractmethod
    def _get_mime_type(self):
        raise NotImplementedError
    
    def _assemble_prompt(self, thing_to_categorize):
        print('assembling prompts')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.CATEGORIZE_SYSTEM_TEMPLATE, 
            user_prompt = prompt_config.CATEGORIZE_HUMAN_TEMPLATE, 
            context = thing_to_categorize
            categories = self.categories 
        )
        return assembled_prompt

    def categories_limit_check(df):
        categories_exceeding_limit = []
        if df is not None:
            df["category"] = df["category"].str.split(", ")
            df_exploded = df.explode("category")

            unique_values_counts = df_exploded["category"].value_counts()
            # print(unique_values_counts)
            for category, count in unique_values_counts.items():
                if count > config.SUBCLASS_THRESHOLD:
                    categories_exceeding_limit.append(category)

    def _extract_full_text(self):
        if self.df_to_categorize is not None:
            try:
                full_text_df = fetch_full_text(category_df['PMID'])
                category_df = pd.merge(category_df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df            
                                                
    def categorize_articles(self, category_df: pd.DataFrame, input_text: str) -> Tuple[pd.DataFrame, Any]:
        # using copy to stop view vs copy warning in pandas
        reduced_df = review_data.get_relevant_rows(category_df).copy()
        input_list = input_text.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]

        for index, row in reduced_df.iterrows():
            data = row[["abstract", "title"]]
            assembled_prompt = self._assemble_prompt(thing_to_categorize=data)
            response, response_meta = self.single_response.generate_response(assembled_prompt)
            self._update_total_cost(response_meta)
            assigned_categories = response.content.replace("'", "")
            reduced_df.loc[index, "category"] = assigned_categories.lower()
        return reduced_df

    def save_results_to_excel(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='wb') as tmpfile:
                category_df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            raise
            
    def recombine_categories(df, df_original):
        # Convert all unique categories to string before forming the list
        unique_values_list = list(df["category"].astype(str).unique())
        # Convert the 'category' column to string
        df["category"] = df["category"].astype(str)
        # remove duplicates, possibly created by multiple categories being subcategorized
        df.drop_duplicates(subset=["PMID", "category"], keep="first", inplace=True)
        # Reverse the explode operation to update original dataframe
        df = df.groupby(df.index).agg({"category": lambda x: ", ".join(x), "Relevant": "first"})

        # Merging other columns back into the df
        df_final = df_original.drop(columns=["category", "Relevant"]).merge(
            df, left_index=True, right_index=True, how="right"
        )
        return df_final, unique_values_list
    
class StreamlitCategorizeManager(BaseCategorizeManager):
    def __init__(self, df, userdefined_categories):
        import streamlit as st
        super().__init__(df,userdefined_categories)
        st.session_state["file_uploaded_cate"] = False
 
    def _download_results(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        st.write("Note that once you hit download, this form will reset.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            write_excel_output(tmpfile, category_df, self.userdefined_categories)
            with open(tmpfile.name, "rb") as file:
                st.balloons()
                st.download_button(
                    label=self.get_download_button_label(),
                    data=file,
                    file_name=self.get_filename(),
                    mime=self._get_mime_type(),
                )  
    
    def _get_filename(self):
        return config.SR_STEP3_FILENAME
    
    def _get_mime_type(self):
        return config.EXCEL_MIME       
  
    def get_download_button_label(self):
        return config.EXCEL_DOWNLOAD_LABEL

    def categorize_articles(self):
        super().categorize_articles()
        if self.df is not None:
            st.session_state["file_uploaded_cate"] = True
            with st.spinner("Categorizing contents of file..."):
                category_df = self.categorize_articles()
            self._download_results(category_df)

    