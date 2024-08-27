from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# from langchain_openai import AzureChatOpenAI
# import os


PUBMED_PROMPT = """Given the following research question, suggest a PubMed search string to find relevant articles:\n\n{}. Make the query sufficiently broad to be used to evaluate novelty of the project. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."""

GENERATE_HUMAN_KEYWORD_PROMPT = """Given the scientific research question, a list of titles of scholarly publications, and a corresponding list of keywords that researchers have identified from relevant articles in a PubMed search, your task is to analyze these inputs and determine three separate lists:

Primary Keywords: These are the most relevant keywords that appear more frequently in the titles and keyword lists and are directly related to the research question. The presence of these keywords in an article title is a strong indicator that it could be useful for the research question.
Secondary Keywords: These are the less frequent but still relevant keywords. They are related to the research question but might not have as direct of a correlation to the main topic as the primary keywords.
Exclusion Keywords: These are the keywords that have the potential to lead the search off-topic. They might be found in the keyword lists but they are not relevant to the research question and may lead to articles that are not useful.

Research Question: \n\n{question}

List of Publication Titles: \n\n{titles}

List of keyword lists: \n\n{keywords_list}

Please provide the primary, secondary, and exclusion keyword lists related to the given research question based on the provided keywords and titles lists from the PubMed search in JSON format. Avoid repeats."""

GENERATE_SYSTEM_KEYWORD_PROMPT = """ You are an expert clinical researcher. """

ITER_PUBMED_PROMPT = """Given the following list of keywords from articles selected by a human, suggest a PubMed search string to find more articles consistent with the relevant keywrods:\n\n{}. Make the query as succint as possible by combining similar keywords into the concepts they represent to return the most closely related articles given the set of keywords. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search string."""

FEW_RESULTS_PROMPT = """\n\n The following query returned no or few results. Please suggest a simpler one (i.e., with fewer query elements).\n\n"""

SUMMARIZE_LITERATURE_PROMPT = """I am considering a clinical research project to address this question: '{}'\n\n I want to understand how my project is situated in existing literature. Write a paragrph summarizing of the following article abstracts and addressing how my proposed project fits in to existing literature.\n\n{}\n\nCite each article in the paragraph in APA format."""

CATEGORIZE_SYSTEM_TEMPLATE = """ Help categorize the input data into the categories given by the user. Return comma separated category(ies) as output. Be parsimonius, assigning only categories that matter the most -- ideally 3 or fewer. Use only the categories given by the user to categorize the input. Even if the article does not fit a category well, pick the best one possible."""

HUMAN_TEMPLATE = """
CONTEXT:
{context}

INPUT CATEGORIES:
{categories}

OUTPUT:
"""

SUMMARIZE_CATEGORY_TEMPLATE = "I am working  on a scoping review to address this question: {question}\n\n Currently, I am summarizing articles by expert-defined categories. All of the article summaries below were assigned the category {category}. Write a one page (or shorter) final summary of the following journal article summaries, focusing on my question. Liberally use APA-style in-text citations throughout the paragraph, citing the summarized articles. The article summaries are separated by '---'"

SUMMARIZE_NEWSLETTER_TEMPLATE = """I am updating the 'Your Monthly AI Digest of the Latest in Anesthesiology Research' newsletter for the subfield of {category}. I will provide you with summaries of recent anesthesiology articles from PubMed. Based on these summaries, I need two specific sections for the newsletter:

#### Key Anesthesiology Insights: 
Please create a 3-item list about the most impactful articles that capture the most critical findings from the provided article summaries. Each bullet entry should be a two to three sentences indicating first the main highlight or takeaway and second who was studied, the type of study, the intervention, and the outcome. At the end, include the PMID as a hyperlink to the PubMed article for further reading. 

#### In-Depth Analysis: 
After the bullet points, delve deeper into additional articles (not covered in the bullet points) and provide detailed insights on their implications for clinical practice in anesthesiology. Cite the articles using PMIDs as a link to the PubMed article for further reading.

Remember, the content should be clear, concise, and targeted towards busy healthcare professionals, providing them with valuable and quick updates on the field of anesthesiology. 

Format your response as markdown. A PubMed hyperlink looks like this in markdown:
[PMID: <PMID>](https://pubmed.ncbi.nlm.nih.gov/<PMID>/)
"""


SUMMARIZE_HUMAN_TEMPLATE = """
Content to summarize:
{content}
"""

SYSTEM_DRAFT_TEMPLATE = """
You are an expert medical writer. Your job is to write a draft of a scoping review article to address this question: {question}\n\n 

You will be given article from summaries (with APA-style citations) made from large sets of categorized articles.

Both the categories and summaries were made by experts.
"""

HUMAN_INTRODUCTION_TEMPLATE = """
Let's work on the introduction. Here are the category summaries with in-text citations:

---
{summaries}
---

Please provide a draft of the introduction for the scoping review article, using in-text citations where appropriate.

Format your response as markdown like this

# Introduction

## Background
List the question to be addressed

## Objectives
Clearly define the objectives of the scoping review.

## Significance
Significance of the findings of the review
"""


HUMAN_CONCLUSION_TEMPLATE = """
Let's work on the Conclusion. Here are the category summaries with in-text citations:

---
{summaries}
---

And here is the Introduction 

---
{introduction}
---

Please provide a draft of the conclusion for the scoping review article, using in-text citations where appropriate.

Format your response as markdown like this

# Conclusion
Summarize the key findings and their implications in a concise manner.

"""

HUMAN_ABSTRACT_TEMPLATE = """
Let's work on the Abstract. Here are the category summaries with in-text citations:

---
{summaries}
---

Here is the Introduction 

---
{introduction}
---

Here is the methdology

---
{methodology}
---
And here is the conclusion

---
{conclusion}
---

Please provide a draft of the abstract for the scoping review article.

Format your response as markdown like this

# Abstract
A brief summary of the review, including the purpose, methodology, main findings, and conclusions.
"""

STANDALONE_SUMMARY_TEMPLATE = "You are a research librarian with medical writing experience. A researchers is considering a clinical research project to address this question: '{question}' They want to and understand how my project is situated in existing literature. Write a paragrph for them summarizing of the following article abstracts and addressing how their proposed project fits in to existing literature. Liberally use APA-style in-text citations throughout the paragraph, citing the articles. The article abstracts are separated by '---'"

standalone_system_message_prompt = SystemMessagePromptTemplate.from_template(
    STANDALONE_SUMMARY_TEMPLATE
)




generate_sys_keywords_prompt = SystemMessagePromptTemplate.from_template(
    GENERATE_SYSTEM_KEYWORD_PROMPT
)
generate_human_keywords_prompt = HumanMessagePromptTemplate.from_template(
    GENERATE_HUMAN_KEYWORD_PROMPT
)

keyword_chat_prompt = ChatPromptTemplate.from_messages(
    [generate_sys_keywords_prompt, generate_human_keywords_prompt]
)


summarize_system_message_prompt = SystemMessagePromptTemplate.from_template(
    SUMMARIZE_CATEGORY_TEMPLATE
)
newsletter_system_message_prompt = SystemMessagePromptTemplate.from_template(
    SUMMARIZE_NEWSLETTER_TEMPLATE
)

sumarize_human_message_prompt = HumanMessagePromptTemplate.from_template(SUMMARIZE_HUMAN_TEMPLATE)

category_summary_chat_prompt = ChatPromptTemplate.from_messages(
    [summarize_system_message_prompt, sumarize_human_message_prompt]
)

standalone_chat_prompt = ChatPromptTemplate.from_messages(
    [standalone_system_message_prompt, sumarize_human_message_prompt]
)

newsletter_chat_prompt = ChatPromptTemplate.from_messages(
    [newsletter_system_message_prompt, sumarize_human_message_prompt]
)

system_message_prompt = SystemMessagePromptTemplate.from_template(CATEGORIZE_SYSTEM_TEMPLATE)
human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE)

categorization_chat_prompt = ChatPromptTemplate.from_messages(
    [system_message_prompt, human_message_prompt]
)

draft_system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_DRAFT_TEMPLATE)

human_introduction_prompt = HumanMessagePromptTemplate.from_template(HUMAN_INTRODUCTION_TEMPLATE)
human_conclusion_prompt = HumanMessagePromptTemplate.from_template(HUMAN_CONCLUSION_TEMPLATE)
human_abstract_prompt = HumanMessagePromptTemplate.from_template(HUMAN_ABSTRACT_TEMPLATE)

draft_introduction_prompt = ChatPromptTemplate.from_messages(
    [draft_system_message_prompt, human_introduction_prompt]
)
draft_conclusion_prompt = ChatPromptTemplate.from_messages(
    [draft_system_message_prompt, human_conclusion_prompt]
)
draft_abstract_prompt = ChatPromptTemplate.from_messages(
    [draft_system_message_prompt, human_abstract_prompt]
)


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
