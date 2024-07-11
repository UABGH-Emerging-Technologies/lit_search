from datetime import datetime
from ScopingReview.SearchManager import BaseSearchManager
from ScopingReview_config import app_config, config, prompt_config
from llm_utils.WorkflowHandler import WorkflowHandler

class ArticleSearch(WorkflowHandler):
    """
    This class handles the workflow for searching articles based on a research question.
    """

    def __init__(self, research_question):
        """
        Initialize the ArticleSearch class with a research question.
        """
        super().__init__()
        self.research_question = research_question
        self.search_manager = BaseSearchManager(scoping_step=1, research_q=research_question)

    def process(self):
        """
        Process the search workflow and return the search results.
        """
        articles_df, query_string = self.search_manager.search_and_compile_articles(write_excel=False)
        return articles_df

    def write_excel_output(self, file_path, articles_df, research_question):
        """
        Write the search results to an Excel file.
        """
        self.search_manager._write_search_results(articles_df, research_question, query_string="")
        with open(file_path, "wb") as f:
            f.write(articles_df.to_excel(index=False))

    def log_to_database(self, app_config, content_to_log, start, finish, background_tasks, label=""):
        """
        Log the search details to the database.
        """
        super().log_to_database(app_config, content_to_log, start, finish, background_tasks, label)

