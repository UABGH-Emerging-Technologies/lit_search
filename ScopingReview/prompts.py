from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

PUBMED_PROMPT = "Given the following research question, suggest a PubMed search string to find relevant articles:\n\n{}. Make the query sufficiently broad to be used to evaluate novelty of the project. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."

ITER_PUBMED_PROMPT = "Given the following list of keywords from articles selected by a human, suggest a PubMed search string to find more articles consistent with the relevant keywrods:\n\n{}. Make the query as succint as possible by combining similar keywords into the concepts they represent to return the most closely related articles given the set of keywords. Return only the pubmed search string, as your response will be used directly as an input to a function that takes in pubmed search strings."

FEW_RESULTS_PROMPT = "\n\n The following query returned no or few results. Please suggest a simpler one (i.e., with fewer query elements).\n\n"

SUMMARIZE_LITERATURE_PROMPT = "I am considering a clinical research project to address this question: '{}'\n\n I want to {} and understand how my project is situated in existing literature. Write a paragrph summarizing of the following article abstracts and addressing how my proposed project fits in to existing literature.\n\n{}\n\nCite each article in the paragraph in APA format."

