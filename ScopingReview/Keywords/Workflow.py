from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponseHandler import SingleResponseHandler
from ScopingReview.Keywords.Manager import KeywordManager

class KeywordWorkflow(WorkflowHandler):
    def __init__(self, df, research_question):
        super().__init__()
        self.df = df
        self.research_question = research_question
        self.keyword_manager = KeywordManager()

    def generate_keywords(self):
        relevant_rows = self.get_relevant_rows()
        all_titles = relevant_rows['title'].tolist()
        formatted_keywords = self.keyword_manager.format_keywords(relevant_rows)

        formatted_prompt = self.keyword_manager.format_prompt(
            question=self.research_question, titles=all_titles, keywords_list=formatted_keywords
        )

        response_handler = SingleResponseHandler()
        result, response_meta = response_handler.get_response(formatted_prompt)

        return result, response_meta
