from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
# from langchain_openai import AzureChatOpenAI
# import os


PUBMED_PROMPT = """Given the following research question, suggest a PubMed search string to find relevant articles:\n\n{}. Make the query sufficiently broad to be used to evaluate novelty of the project. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."""

GENERATE_HUMAN_KEYWORD_PROMPT = """Given the scientific research question, a list of titles of scholarly publications, and a corresponding list of lists of keywords, each corresponding to a specific scholarly work from a PubMed search, your task is to analyze these inputs and determine three separate lists:

Primary Keywords: These are the most relevant keywords that appear more frequently in the titles and keyword lists and are directly related to the research question. The presence of these keywords in an article title is a strong indicator that it could be useful for the research question.
Secondary Keywords: These are the less frequent but still relevant keywords. They are related to the research question but might not have as direct of a correlation to the main topic as the primary keywords.
Exclusion Keywords: These are the keywords that have the potential to lead the search off-topic. They might be found in the keyword lists but they are not relevant to the research question and may lead to articles that are not useful.

Research Question: \n\n{question}

List of Publication Titles: \n\n{titles}

List of keyword lists: \n\n{keywords_list}

Please provide the primary, secondary, and exclusion keyword lists related to the given research question based on the provided keywords and titles lists from the PubMed search in JSON format."""

GENERATE_SYSTEM_KEYWORD_PROMPT = """ You are an expert clinical researcher. """

ITER_PUBMED_PROMPT = """Given the following list of keywords from articles selected by a human, suggest a PubMed search string to find more articles consistent with the relevant keywrods:\n\n{}. Make the query as succint as possible by combining similar keywords into the concepts they represent to return the most closely related articles given the set of keywords. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search string."""

FEW_RESULTS_PROMPT = """\n\n The following query returned no or few results. Please suggest a simpler one (i.e., with fewer query elements).\n\n"""

SUMMARIZE_LITERATURE_PROMPT = """I am considering a clinical research project to address this question: '{}'\n\n I want to {} and understand how my project is situated in existing literature. Write a paragrph summarizing of the following article abstracts and addressing how my proposed project fits in to existing literature.\n\n{}\n\nCite each article in the paragraph in APA format."""

CATEGORIZE_SYSTEM_TEMPLATE = """ Help categorize the input data into either of the categories given by the user and return only 1 category as output(whichever matters the most)."""

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

generate_sys_keywords_prompt = SystemMessagePromptTemplate.from_template(GENERATE_SYSTEM_KEYWORD_PROMPT)

generate_human_keywords_prompt = HumanMessagePromptTemplate.from_template(GENERATE_HUMAN_KEYWORD_PROMPT)

keyword_chat_prompt = ChatPromptTemplate.from_messages([generate_sys_keywords_prompt,generate_human_keywords_prompt])

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