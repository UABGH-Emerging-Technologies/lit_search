from ScopingReview.InitialSearch.Workflow import ArticleSearch
from aiweb_common.WorkflowHandler import WorkflowHandler
from aiweb_common.generate.SingleResponse import SingleResponseHandler
import ScopingReview_config.config as config
import ScopingReview_config.prompt_config as prompt_config
from aiweb_common.file_operations.text_format import convert_markdown_docx
import tempfile




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
        articles_df = self.searcher.process()
        self.total_cost += self.searcher.total_cost
        summary_body = self.summarize_from_abstracts(articles_df)
        docx_data = self.format_response(summary_body.content, articles_df)
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None
        