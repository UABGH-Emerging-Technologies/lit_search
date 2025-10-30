from aiweb_common.generate.SingleResponse import SingleResponseHandler
from aiweb_common.WorkflowHandler import WorkflowHandler
from ScopingReview.Keywords.Manager import KeywordData, KeywordManager
from ScopingReview_config import config, prompt_config


class KeywordWorkflow(WorkflowHandler):
    def __init__(
        self,
        df,
        research_question,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
    ):
        super().__init__()
        self.df = df
        self.research_question = research_question
        
        # Initialize LLM with dynamic configuration (like IRB Assistant)
        self._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="KeywordWorkflow"
        )
        
        # Use self.llm_interface instead of config.SMART_LLM_INTERFACE
        self.single_response = SingleResponseHandler(self.llm_interface)
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
        response, response_meta = self.single_response.generate_response(assembled_prompt)
        print("Response - ", response.content)
        self._update_total_cost(response_meta)
        return response.content

    def process(self):
        print("Generating Keywords")
        generated_keywords_json = self.initialize_keywords()
        print(generated_keywords_json)
        primary, secondary, exclusion = self.keyword_manager.parse_keywords(
            str(generated_keywords_json)
        )
        keywords = KeywordData(
            primary_keywords=primary, secondary_keywords=secondary, exclusion_keywords=exclusion
        )
        return keywords