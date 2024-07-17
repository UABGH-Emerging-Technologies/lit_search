from aiweb_common.WorkflowHandler import WorkflowHandler
import tempfile
from ScopingReview_config import config
import ScopingReview_config.prompt_config as prompt_config
import ScopingReview_config.boilerplate as boilerplate_config
from ScopingReview.Draft.Manager import DraftReviewManager
from aiweb_common.file_operations.text_format import convert_markdown_docx
from aiweb_common.generate.SingleResponse import SingleResponseHandler

# This Python class `DraftReview` handles the drafting process of a research review by assembling
# prompts for introduction, conclusion, and abstract, generating responses, and assembling the final
# document.
class DraftReview(WorkflowHandler):
    def __init__(self, summaries, research_q):
        super().__init__()
        self.summaries = summaries
        self.research_q = research_q
        self.drafter = DraftReviewManager(summaries, research_q)
        self.single_response = SingleResponseHandler(config.LLM_INTERFACE)

    def draft_review(self):
        if self.summaries is not None:
            markdown_to_convert = self.write_first_draft()
            return markdown_to_convert
        
    def assemble_intro_prompt(self, summaries_no_bib):
        print('assembling intro prompt')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SYSTEM_DRAFT_TEMPLATE,
            user_prompt = prompt_config.HUMAN_INTRODUCTION_TEMPLATE,
            question = self.research_q,
            summaries = "\n\n".join(summaries_no_bib)
        )
        return assembled_prompt
    
    def assemble_conclusion_prompt(self, summaries_no_bib, intro):
        print('assembling conclusion prompt')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SYSTEM_DRAFT_TEMPLATE, 
            user_prompt = prompt_config.HUMAN_CONCLUSION_TEMPLATE, 
            question = self.research_q,
            summaries = "\n\n".join(summaries_no_bib),
            introduction = intro
        )
        return assembled_prompt
    
    def assemble_abstract_prompt(self, summaries_no_bib, intro, conclusion):
        print('assembling abstract prompt')
        assembled_prompt = self.single_response.single_response_service.preparer.assemble_prompt(
            system_prompt = prompt_config.SYSTEM_DRAFT_TEMPLATE, 
            user_prompt = prompt_config.HUMAN_ABSTRACT_TEMPLATE, 
            question = self.research_q,
            summaries = "\n\n".join(summaries_no_bib),
            introduction = intro,
            methodology = boilerplate_config.METHODOLOGY,
            conclusion = conclusion
        )
        return assembled_prompt

    def write_first_draft(self):
        """
        This function generates a first draft of a document by extracting citations, preparing
        introduction, conclusion, and abstract prompts, generating responses, and assembling the
        document with the provided content.
        
        Returns:
          The `write_first_draft` method returns the assembled draft document, which includes the
        abstract, introduction, methodology, results, conclusion, and citations in Markdown format.
        """
        citations, non_citations = self.drafter.extract_apa_citations(self.summaries)
        
        # prep introduction
        intro_prompt = self.assemble_intro_prompt(non_citations)
        intro, intro_response_meta = self.single_response.generate_response(intro_prompt)
        self._update_total_cost(intro_response_meta)
        
        # prep conclusion
        conclusion_prompt = self.assemble_conclusion_prompt(non_citations, intro)
        conclusion, conclusion_response_meta = self.single_response.generate_response(conclusion_prompt)
        self._update_total_cost(conclusion_response_meta)
        
        # prep abstract 
        abstract_prompt = self.assemble_abstract_prompt(non_citations, intro, conclusion)
        abstract, abstract_response_meta = self.single_response.generate_response(abstract_prompt)
        self._update_total_cost(abstract_response_meta)

        assembled_draft = self.drafter.assemble_document(
            abstract_md = abstract.content,
            intro_md = intro.content,
            methods_md = boilerplate_config.METHODOLOGY,
            results_md = non_citations,
            conclusion_md = conclusion.content,
            citations_md = citations
        )

        return assembled_draft


    def process(self):
        draft_md = self.draft_review()
        return draft_md
