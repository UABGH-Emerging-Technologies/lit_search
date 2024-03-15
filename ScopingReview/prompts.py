from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
# from langchain_openai import AzureChatOpenAI
# import os


PUBMED_PROMPT = "Given the following research question, suggest a PubMed search string to find relevant articles:\n\n{}. Make the query sufficiently broad to be used to evaluate novelty of the project. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."

ITER_PUBMED_PROMPT = "Given the following list of keywords from articles selected by a human, suggest a PubMed search string to find more articles consistent with the relevant keywrods:\n\n{}. Make the query as succint as possible by combining similar keywords into the concepts they represent to return the most closely related articles given the set of keywords. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search string."

FEW_RESULTS_PROMPT = "\n\n The following query returned no or few results. Please suggest a simpler one (i.e., with fewer query elements).\n\n"

SUMMARIZE_LITERATURE_PROMPT = "I am considering a clinical research project to address this question: '{}'\n\n I want to {} and understand how my project is situated in existing literature. Write a paragrph summarizing of the following article abstracts and addressing how my proposed project fits in to existing literature.\n\n{}\n\nCite each article in the paragraph in APA format."

CATEGORIZE_SYSTEM_TEMPLATE = """ Help categorize the input data into either of the categories given by the user. Return comma separated category(ies) as output(assign categories that matters the most)."""

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





summarize_system_message_prompt = SystemMessagePromptTemplate.from_template(SUMMARIZE_CATEGORY_TEMPLATE)
sumarize_human_message_prompt = HumanMessagePromptTemplate.from_template(SUMMARIZE_HUMAN_TEMPLATE)

category_summary_chat_prompt = ChatPromptTemplate.from_messages([summarize_system_message_prompt, sumarize_human_message_prompt])

system_message_prompt = SystemMessagePromptTemplate.from_template(CATEGORIZE_SYSTEM_TEMPLATE)
human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE)

categorization_chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

draft_system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_DRAFT_TEMPLATE)

human_introduction_prompt = HumanMessagePromptTemplate.from_template(HUMAN_INTRODUCTION_TEMPLATE)
human_conclusion_prompt = HumanMessagePromptTemplate.from_template(HUMAN_CONCLUSION_TEMPLATE)
human_abstract_prompt = HumanMessagePromptTemplate.from_template(HUMAN_ABSTRACT_TEMPLATE)

draft_introduction_prompt = ChatPromptTemplate.from_messages([draft_system_message_prompt, human_introduction_prompt])
draft_conclusion_prompt = ChatPromptTemplate.from_messages([draft_system_message_prompt, human_conclusion_prompt])
draft_abstract_prompt = ChatPromptTemplate.from_messages([draft_system_message_prompt, human_abstract_prompt])



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