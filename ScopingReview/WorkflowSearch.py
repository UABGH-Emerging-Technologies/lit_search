from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
from ScopingReview_config import config, prompt_config
import ScopingReview.data as review_data
from aiweb_common.resource.PubMedInterface import PubMedInterface
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
import pandas as pd

class ArticleSearch(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.article_ids = []
        self.research_question = research_question

    def _make_initial_df(self, pm_connection, article_ids):
        articles_df = pm_connection.fetch_article_details(article_ids)

        # add author response column
        articles_df.insert(0, "Author 1: Relevant Article? (Yes/No)", "No")
        articles_df.insert(1, "Author 2: Relevant Article? (Yes/No)", "No")

        articles_df.rename(columns={"pmid": "PMID"}, inplace=True)

        return articles_df
    
    def _search_and_compile(self, query):
        pm_connection = PubMedInterface(
            email=config.DEV_EMAIL,
            max_results=config.MAX_ARTICLES_SR,
            streamlit_context=True,
        )
        print("query - ",query)
        article_ids_new = pm_connection.search_pubmed_articles(query)
        print(article_ids_new)
        article_ids = list(set().union(self.article_ids, article_ids_new))
        articles_df = self._make_initial_df(pm_connection, article_ids)
        return articles_df
    
    
    def write_excel_output(tmpfile, df, input_search_terms, query_strings=""):
        with pd.ExcelWriter(tmpfile.name, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")

            # Convert string to dataFrame and save to excel
            data = {"Input Terms": [input_search_terms], "PubMed Querey": [query_strings]}
            df_keywords = pd.DataFrame(data)
            df_keywords.to_excel(writer, index=False, sheet_name="Sheet2")

            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet1 = writer.sheets["Sheet1"]
            worksheet2 = writer.sheets["Sheet2"]
            # Define a format with word wrap
            wrap_format = workbook.add_format({"text_wrap": True})

            # Iterate over the DataFrame columns to set the column width
            for idx, col in enumerate(df.columns):
                # Find the maximum length of data in the column
                column_len = df[col].astype(str).map(len).max()
                column_title_len = len(col)
                max_len = min(100, max(column_len, column_title_len))

                # Set the column width with some extra margin
                worksheet1.set_column(idx, idx, max_len + 1, wrap_format)

            # You can also set column width for the second sheet if needed
            worksheet2.set_column(0, 0, len("Unique Keywords") + 1, wrap_format)

    def process(self):
        # Gather references from PubMed
        single_response = SingleResponseHandler(config.LLM_INTERFACE)
        
        print('Assembling prompts')
        assembled_prompt = single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.PUBMED_SYSTEM_PROMPT,
            user_prompt=prompt_config.PUBMED_HUMAN_PROMPT,
            text=self.research_question
        )
        
        response, response_meta = single_response.generate_response(assembled_prompt)
        self._update_total_cost(response_meta)
        articles_df = self._search_and_compile(response.content)
        return articles_df
