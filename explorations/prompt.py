from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os

def prompt_defn():
    chat = AzureChatOpenAI(
        azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
        openai_api_version="2023-06-01-preview",
        azure_deployment="ChatGPT4",
        openai_api_type="azure",
        temperature=0,
        model_name="gpt-4",
        api_key= os.environ.get("OPENAI_API_KEY")
    )

    system_template = """ Help categorize the text file into either of the input categories given by the user and return 1 category as output."""


    human_template = """
    CONTEXT:
    {context}

    INPUT CATEGORIES:
    {categories}

    OUTPUT:
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
