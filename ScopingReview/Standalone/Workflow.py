from ScopingReview.InitialSearch.Workflow import ArticleSearch
from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
import ScopingReview_config.config as config
import ScopingReview_config.prompt_config as prompt_config
from aiweb_common.file_operations.text_format import convert_markdown_docx
import tempfile




# This Python class `StandaloneSummary` is designed to handle the process of summarizing articles
# based on abstracts for a given research question.
class StandaloneSummary(WorkflowHandler):
    def __init__(self, research_question):
        super().__init__()
        self.research_question = research_question
        self.searcher = ArticleSearch(research_question)
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)
        
    def format_response(self, summary, df):
        output = str(
            "# Literature summary \n\n"
            + "_" + str(self.research_question) + "_ \n\n"
            + str(summary)
            + "\n\n"
            + "## Works consulted"
            + "\n\n"
            + "\n\n".join(df.citation)
        )
        docx_data = convert_markdown_docx(output)
        return docx_data
        
        
    def assemble_standalone_prompt(self, abstracts):
        print('assembling standalone prompt')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.STANDALONE_SUMMARY_TEMPLATE, 
            user_prompt = prompt_config.SUMMARIZE_HUMAN_TEMPLATE, 
            question = self.research_question,
            content = abstracts
        )
        return assembled_prompt
    
        
    def summarize_from_abstracts(self, articles_df):
        """
        This function takes a DataFrame of articles with abstracts, extracts the abstracts, assembles
        them into a text to summarize, generates a summary using a single response model, and returns
        the summary.
        
        Args:
          articles_df: The `summarize_from_abstracts` function takes in a DataFrame `articles_df`
        containing articles with columns like 'citation' and 'abstract'. It iterates over each row in
        the DataFrame, extracts the citation and abstract information, assembles them into a formatted
        text, and then generates a summary
        
        Returns:
          The `summarize_from_abstracts` method returns the summary generated from the abstracts of
        articles in the provided DataFrame `articles_df`.
        """
        article_abstracts = []
        for _, row in articles_df.iterrows():

            articles_df = (
                f"APA Citation: {row.citation}\n\n Abstract: {row.abstract}\n\n --- "
            )
            article_abstracts.append(articles_df)
        text_to_summarize = "\n\n".join(article_abstracts)
        standalone_prompt = self.assemble_standalone_prompt(text_to_summarize)
        summary, response_meta = self.single_response.generate_response(standalone_prompt)
        self._update_total_cost(response_meta)
        return summary

    def process(self):
        """
        The `process` function retrieves articles, summarizes them, formats the response, and returns a
        temporary file path for a Word document if successful.
        
        Returns:
          The `process` method returns the name of a temporary DOCX file that is created with the summarized
        content from the abstracts of articles processed by the `searcher`. If the `docx_data` is
        successfully created, the method returns the name of the temporary DOCX file. If `docx_data` is
        `None`, then the method returns `None`.
        """
        articles_df = self.searcher.process()
        self.total_cost += self.searcher.total_cost
        summary_body = self.summarize_from_abstracts(articles_df)
        docx_data = self.format_response(summary_body.content, articles_df)
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None
        