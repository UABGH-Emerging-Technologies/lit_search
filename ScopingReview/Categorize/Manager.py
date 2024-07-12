import ScopingReview_config.prompt_config as prompt_config
import ScopingReview_config.boilerplate as boilerplate
from ScopingReview.BaseManager import BaseManager
import ScopingReview_config.config as config
import pandas as pd
import tempfile
from typing import Tuple, Any

from llm_utils import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler

#TODO move aiweb_common stuff to Categorize.Workflow
class BaseCategorizeManager(BaseManager):
    def __init__(self, df_to_categorize, userdefined_categories):
        super().__init__(df_to_categorize)
        # convert comma separated values to list and store as self.categories
        input_list = userdefined_categories.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        self.categories = input_list
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)
    
    def _get_filename(self):
        return config.SR_STEP3_FILENAME
    
    def _get_mime_type(self):
        return config.EXCEL_MIME   
    
    def _assemble_prompt(self, thing_to_categorize):
        print('assembling prompts')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.CATEGORIZE_SYSTEM_TEMPLATE, 
            user_prompt = prompt_config.CATEGORIZE_HUMAN_TEMPLATE, 
            context = thing_to_categorize,
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
        if self.df is not None:
            try:
                full_text_df = self.fetch_full_text(self.df['PMID'])
                category_df = pd.merge(self.df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df            

    #TODO move this to workfow (since it calls on llm_utils)                                                
    def categorize_articles(self, category_df: pd.DataFrame, input_text: str) -> Tuple[pd.DataFrame, Any]:
        # using copy to stop view vs copy warning in pandas
        reduced_df = self.get_relevant_rows(self.df).copy()
        input_list = input_text.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]

        for index, row in reduced_df.iterrows():
            data = row[["abstract", "title"]]
            assembled_prompt = self._assemble_prompt(thing_to_categorize=data)
            response, response_meta = self.single_response.generate_response(assembled_prompt)
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
    

    def sub_categorize(categories_exceeding_limit, sub_categories):
        df_copy = self.df.copy()
        reduced_df = self.get_relevant_rows(df_copy)
        # should already be transformed to a python list by categories_limit_check()
        df_exploded = reduced_df.explode("category")

        # Prepare new sub-categories
        sub_categories = [value.strip() for value in sub_categories.split(",") if value.strip()]
        # Replace categories exceeding limit with sub-categories
        for remove_category in categories_exceeding_limit:
            remove_category = remove_category.strip()
            remove_category = remove_category.lower()
            df_exploded["category"] = df_exploded["category"].str.lower()
            mask = df_exploded["category"] == remove_category
            for index, row in df_exploded[mask].iterrows():
                # index is preserved across the explode
                if row.category == remove_category:
                    data = row[["abstract", "title"]]
                    # TODO Move this stuff to Workflow
                    with get_openai_callback() as response_meta:
                        result = lit_config.CHAT35.invoke(
                            lit_prompts.categorization_chat_prompt.format_prompt(
                                categories=sub_categories, context=data
                            ).to_messages()
                        )
                    category_to_write = result.content.replace("'", "")
                    df_exploded.at[index, "category"] = category_to_write.lower()

        df_final, unique_values_list = recombine_categories(df_exploded, df_copy)

        return df_final, "".join(map(str, unique_values_list)), response_meta


class FastAPICategorizeManager(BaseCategorizeManager):
    def __init__(self, df: pd.DataFrame, userdefined_categories: str):
        super().__init__(df, userdefined_categories)

    def categorize_articles_and_save(self) -> str:
        """
        Perform the categorization and save the results to an Excel file.
        Returns the path to the Excel file.
        """
        try:
            category_df = self.categorize_articles()
            if category_df.empty:
                raise HTTPException(status_code=404, detail="No data to categorize or articles not found.")
            return self.save_results_to_excel(category_df)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def save_results_to_excel(self, category_df: pd.DataFrame) -> str:
        """
        Save the categorized DataFrame to an Excel file and return the file path.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='w+b') as tmpfile:
                write_excel_output(tmpfile, category_df, self.userdefined_categories)
                return tmpfile.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
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
      
  
    def get_download_button_label(self):
        return config.EXCEL_DOWNLOAD_LABEL

    def categorize_articles(self):
        super().categorize_articles()
        if self.df is not None:
            st.session_state["file_uploaded_cate"] = True
            with st.spinner("Categorizing contents of file..."):
                category_df = self.categorize_articles()
            self._download_results(category_df)

    