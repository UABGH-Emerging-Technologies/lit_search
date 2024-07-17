import ScopingReview_config.prompt_config as prompt_config
import ScopingReview_config.boilerplate as boilerplate
from ScopingReview.BaseManager import BaseManager
import ScopingReview_config.config as config
import pandas as pd
import tempfile
from typing import Tuple, Any
from fastapi import HTTPException  # Importing HTTPException


#TODO move aiweb_common stuff to Categorize.Workflow
# The `BaseCategorizeManager` class defines methods for categorizing data, assembling prompts,
# extracting full text, and saving results to an Excel file.
class BaseCategorizeManager(BaseManager):
    def __init__(self, df_to_categorize, userdefined_categories):
        super().__init__(df_to_categorize)
        # convert comma separated values to list and store as self.categories
        input_list = userdefined_categories.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        self.categories = input_list
    
    def _get_filename(self):
        return config.SR_STEP3_FILENAME
    
    def _get_mime_type(self):
        return config.EXCEL_MIME   
    
    def _assemble_prompt(self, thing_to_categorize):
        """
        The function `_assemble_prompt` assembles a prompt using system and user templates, along with
        context and categories.
        
        Args:
          thing_to_categorize: `thing_to_categorize` is the object or item that needs to be categorized. It
        is used as context in assembling the prompt for categorization.
        
        Returns:
          The function `_assemble_prompt` returns the assembled prompt that is generated based on the input
        parameters provided to the function.
        """
        print('assembling prompts')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.CATEGORIZE_SYSTEM_TEMPLATE, 
            user_prompt = prompt_config.CATEGORIZE_HUMAN_TEMPLATE, 
            context = thing_to_categorize,
            categories = self.categories 
        )
        return assembled_prompt

    def _extract_full_text(self):
        """
        The function `_extract_full_text` fetches full text data based on PMID and merges it with the
        existing DataFrame.
        
        Returns:
          The method `_extract_full_text` is returning the `category_df` DataFrame after merging the
        original DataFrame `self.df` with the full text DataFrame fetched using the 'PMID' column.
        """
        if self.df is not None:
            try:
                full_text_df = self.fetch_full_text(self.df['PMID'])
                category_df = pd.merge(self.df, full_text_df, on='PMID', how='inner')
            except Exception as e:
                print(f"Failed while getting full texts: {str(e)}")
            return category_df            


    def save_results_to_excel(self, category_df):
        """
        The function `save_results_to_excel` saves a DataFrame to an Excel file with unique PMID values.
        
        Args:
          category_df: The `category_df` parameter is a pandas DataFrame containing data related to
        categories. The data should have a column named "PMID" which is used to drop duplicate rows based on
        the values in this column. The function `save_results_to_excel` takes this DataFrame as input,
        removes duplicate rows based
        
        Returns:
          The `save_results_to_excel` method returns the name of the temporary Excel file that was created
        and saved with the data from the `category_df` DataFrame.
        """
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode='wb') as tmpfile:
                category_df.to_excel(tmpfile.name, index=False)
                return tmpfile.name
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            raise

# This class is a FastAPI manager that categorizes articles and saves the results to an Excel file.
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


            
# class StreamlitCategorizeManager(BaseCategorizeManager):
#     def __init__(self, df, userdefined_categories):
#         import streamlit as st
#         super().__init__(df,userdefined_categories)
#         st.session_state["file_uploaded_cate"] = False
 
#     def _download_results(self, category_df):
#         import streamlit as st  # Ensure streamlit is imported within the method
#         category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
#         st.write("Note that once you hit download, this form will reset.")
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
#             write_excel_output(tmpfile, category_df, self.userdefined_categories)
#             with open(tmpfile.name, "rb") as file:
#                 st.balloons()
#                 st.download_button(
#                     label=self.get_download_button_label(),
#                     data=file,
#                     file_name=self.get_filename(),
#                     mime=self._get_mime_type(),
#                 )  
      
  
#     def get_download_button_label(self):
#         return config.EXCEL_DOWNLOAD_LABEL

#     def categorize_articles(self):
#         import streamlit as st  # Ensure streamlit is imported within the method
#         super().categorize_articles()
#         if self.df is not None:
#             st.session_state["file_uploaded_cate"] = True
#             with st.spinner("Categorizing contents of file..."):
#                 category_df = self.categorize_articles()
#             self._download_results(category_df)
