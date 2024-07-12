from llm_utils.WorkflowHandler import WorkflowHandler

class KeywordWorkflow(WorkflowHandler):
    
    
    #TODO rework this to use new llm_utils
    def generate_keywords(self):
        relevant_rows = self.get_relevant_rows()


        # Format the prompt with deduplicated and counted titles and keywords
        formatted_prompt = lit_prompts.keyword_chat_prompt.format_prompt(
            question=research_question, titles=all_titles, keywords_list=formatted_keywords
        )
        
        with get_openai_callback() as response_meta:
            result = lit_config.CHAT35.invoke(formatted_prompt.to_messages())

        return result.content, response_meta