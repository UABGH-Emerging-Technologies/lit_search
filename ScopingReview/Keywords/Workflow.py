from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler

from ScopingReview.Keywords.Manager import KeywordData, KeywordManager
from ScopingReview_config import config, prompt_config


class KeywordWorkflow(WorkflowHandler):
    def __init__(self, df, research_question):
        super().__init__()
        self.df = df
        self.research_question = research_question
        self.single_response = SingleResponseHandler(config.SMART_LLM_INTERFACE)
        self.keyword_manager = KeywordManager(self.df, self.research_question)

    def initialize_keywords(self):
        relevant_rows = self.keyword_manager.get_relevant_rows()
        all_titles = relevant_rows["title"].tolist()
        formatted_keywords = self.keyword_manager.format_keywords(relevant_rows)
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt=prompt_config.GENERATE_SYSTEM_KEYWORD_PROMPT,
            user_prompt=prompt_config.GENERATE_HUMAN_KEYWORD_PROMPT,
            question=self.research_question,
            titles=all_titles,
            keywords_list=formatted_keywords,
        )
        # print("Assembled prompt - ", assembled_prompt)
        response, response_meta = self.single_response.generate_response(assembled_prompt)
        print("Response - ", response.content)
        self._update_total_cost(response_meta)
        return response.content

    def process(self):
        print("Generating Keywords")
        generated_keywords_json = self.initialize_keywords()
        print(generated_keywords_json)
        # TODO: should this return the three lists?
        primary, secondary, exclusion = self.keyword_manager.parse_keywords(
            str(generated_keywords_json)
        )
        keywords = KeywordData(
            primary_keywords=primary, secondary_keywords=secondary, exclusion_keywords=exclusion
        )
        return keywords
