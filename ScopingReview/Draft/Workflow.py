from aiweb_common.WorkflowHandler import WorkflowHandler
import tempfile
from ScopingReview_config import config
from aiweb_common.generate import write_first_draft
from aiweb_common.file_operations.text_format import convert_markdown_docx

class DraftReview(WorkflowHandler):
    def __init__(self, summaries, research_q):
        super().__init__()
        self.summaries = summaries
        self.research_q = research_q

    def draft_review(self):
        if self.summaries is not None:
            markdown_to_convert, response_meta = write_first_draft(
                self.summaries, self.research_q
            )
            docx_data = convert_markdown_docx(markdown_to_convert)
            self._update_total_cost(response_meta)
            return docx_data

    #TODO map this over to revise LLM_Utils
    def write_first_draft(summaries_markdown, user_question):
        citations, non_citations = extract_apa_citations(summaries_markdown)
        with get_openai_callback() as response_meta:
            introduction_result = lit_config.SUMMARIZE_CHAT.invoke(
                lit_prompts.draft_introduction_prompt.format_prompt(
                    question=user_question, summaries="\n\n".join(non_citations)
                ).to_messages()
            )

            conclusion_result = lit_config.SUMMARIZE_CHAT.invoke(
                lit_prompts.draft_conclusion_prompt.format_prompt(
                    question=user_question,
                    summaries="\n\n".join(non_citations),
                    introduction=introduction_result.content,
                ).to_messages()
            )

            abstract_result = lit_config.SUMMARIZE_CHAT.invoke(
                lit_prompts.draft_abstract_prompt.format_prompt(
                    question=user_question,
                    summaries="\n\n".join(non_citations),
                    introduction=introduction_result.content,
                    methodology=lit_boilerplate.METHODOLOGY,
                    conclusion=conclusion_result.content,
                ).to_messages()
            )

        assembled_draft = (
            abstract_result.content
            + "\n\n"
            + introduction_result.content
            + "\n\n"
            + lit_boilerplate.METHODOLOGY
            + "\n\n"
            + "# Results/Discussion \n\n"
            + "\n\n".join(non_citations)
            + "\n\n"
            + conclusion_result.content
            + "\n\n"
            + "# References \n\n"
            + "\n\n".join(citations)
        )

        return assembled_draft


    def process(self):
        docx_data = self.draft_review()
        if docx_data is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmpfile:
                tmpfile.write(docx_data)
                return tmpfile.name
        return None
