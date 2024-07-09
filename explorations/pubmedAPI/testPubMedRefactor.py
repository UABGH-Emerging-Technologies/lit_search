from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
from ScopingReview_config import app_config
from langchain_openai import AzureChatOpenAI

LLM_INTERFACE = AzureChatOpenAI(
    azure_endpoint="https://nlp-ai-svc.openai.azure.com/",
    openai_api_version="2024-02-01",
    deployment_name="ChatGPT4",
    openai_api_type="azure",
    temperature=0,
    model_name="gpt-4",
    openai_api_key = app_config.GPT4_KEY
)

q = "What are the recent advancements in the application of machine learning techniques in perioperative medicine?"
pmg = PubMedQueryGenerator(LLM_INTERFACE, q)
search_string = pmg.generate_search_string()
print(search_string)