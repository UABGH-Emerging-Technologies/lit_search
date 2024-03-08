from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import AzureChatOpenAI
import os


PUBMED_PROMPT = "Given the following research question, suggest a PubMed search string to find relevant articles:\n\n{}. Make the query sufficiently broad to be used to evaluate novelty of the project. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."

ITER_PUBMED_PROMPT = "Given the following list of keywords from articles selected by a human, suggest a PubMed search string to find more articles consistent with the relevant keywrods:\n\n{}. Make the query as succint as possible by combining similar keywords into the concepts they represent to return the most closely related articles given the set of keywords. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search string."

FEW_RESULTS_PROMPT = "\n\n The following query returned no or few results. Please suggest a simpler one (i.e., with fewer query elements).\n\n"

SUMMARIZE_LITERATURE_PROMPT = "I am considering a clinical research project to address this question: '{}'\n\n I want to {} and understand how my project is situated in existing literature. Write a paragrph summarizing of the following article abstracts and addressing how my proposed project fits in to existing literature.\n\n{}\n\nCite each article in the paragraph in APA format."

CATEGORIZE_SYSTEM_TEMPLATE = """ Help categorize the abstract into either of the input categories given by the user and return only 1 category as output(whichever matters the most) without the quotes. When it is just "No abstract available" in the input return "No abstract available" as output. """

HUMAN_TEMPLATE = """
CONTEXT:
{context}

INPUT CATEGORIES:
{categories}

OUTPUT:
"""

SUMMARIZE_CATEGORY_TEMPLATE = "I am working  on a scoping review to address this question: {question}\n\n Currently, I am summarizing articles by expert-defined categories. All of the article summaries below were assigned the category {category}. Write a single paragrph final summary of the following journal article summaries, focusing on my question. Liberally use APA-style in-text citations throughout the paragraph, citing the summarized articles. The article summaries are separated by '---'"

SUMMARIZE_HUMAN_TEMPLATE = """
Content to summarize:
{content}
"""

summarize_system_message_prompt = SystemMessagePromptTemplate.from_template(SUMMARIZE_CATEGORY_TEMPLATE)

sumarize_human_message_prompt = HumanMessagePromptTemplate.from_template(SUMMARIZE_HUMAN_TEMPLATE)

category_summary_chat_prompt = ChatPromptTemplate.from_messages([summarize_system_message_prompt, sumarize_human_message_prompt])

system_message_prompt = SystemMessagePromptTemplate.from_template(CATEGORIZE_SYSTEM_TEMPLATE)
human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE)

categorization_chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])


# Template for the initial summarization of the first chunk
initial_summary_prompt = """I am working on a scoping review to address a specific question.
I need to summarize this journal article, focusing on the given question and the article's category.
Here is the first chunk of the journal article:

{text}
"""

# Template for refining the summary with each subsequent chunk
refine_summary_prompt = """Based on the existing summary and the specific question, refine the summary with the information from the next chunk of the article.
Current summary:

{existing_summary}

Next chunk of the article:
------------
{text}
------------
"""