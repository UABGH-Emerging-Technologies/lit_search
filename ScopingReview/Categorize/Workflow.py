import tempfile
from typing import Any, Tuple
import pandas as pd
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler, extract_response_text
from ScopingReview.Categorize.Manager import FastAPICategorizeManager
from ScopingReview_config import config, prompt_config
from ScopingReview_config.config import REASONING_EFFORT, _is_responses_api_model


class CategorizeWorkflow(WorkflowHandler):
    def __init__(
        self,
        df,
        userdefined_categories,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__()
        self.df = df
        self.userdefined_categories = userdefined_categories
        self.manager = FastAPICategorizeManager(self.df, self.userdefined_categories)
        
        # Initialize LLM with dynamic configuration (like IRB Assistant)
        _use_responses = _is_responses_api_model(openai_compatible_model)
        self._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="CategorizeWorkflow",
            use_responses_api=_use_responses,
            reasoning_effort=REASONING_EFFORT if _use_responses else None,
        )
        
        # Use self.llm_interface instead of config.FAST_LLM_INTERFACE
        self.single_response = SingleResponseHandler(self.llm_interface)

    def _prep_df_for_categorization(self):
        reduced_df = self.manager.get_relevant_rows().copy()
        return reduced_df

    def _prep_categorylist(self):
        input_list = self.userdefined_categories.split(",")
        input_list = [value.strip() for value in input_list if value.strip()]
        return input_list

    def categorize_articles(self):
        reduced_df = self._prep_df_for_categorization()
        input_list = self._prep_categorylist()
        for index, row in reduced_df.iterrows():
            data = row[["abstract", "title"]]
            assembled_prompt = (
                self.single_response.single_response_service.preparer.assemble_prompt(
                    system_prompt=prompt_config.CATEGORIZE_SYSTEM_TEMPLATE,
                    user_prompt=prompt_config.CATEGORIZE_HUMAN_TEMPLATE,
                    context=data,
                    categories=input_list,
                )
            )
            response, response_meta = self.single_response.generate_response(assembled_prompt)
            self._update_total_cost(response_meta)
            assigned_categories = extract_response_text(response.content).replace("'", "")
            reduced_df.loc[index, "category"] = assigned_categories.lower()
        try:
            print("Fetching Full Texts")
            full_text_df = self.manager.fetch_full_text(reduced_df["PMID"])
            category_df = pd.merge(reduced_df, full_text_df, on="PMID", how="inner")
        except Exception as e:
            print(f"Failed while getting full texts: {str(e)}")
        return category_df

    def get_tempfile_excel(self, category_df):
        category_df.drop_duplicates(subset="PMID", keep="first", inplace=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmpfile:
            self.manager.write_excel_output(
                tmpfile=tmpfile.name,
                df=category_df,
                input_search_terms=self.userdefined_categories,
                query_strings="Generated query strings"
            )
        return tmpfile.name

    def process(self):
        if self.df is not None:
            category_df = self.categorize_articles()
            return category_df