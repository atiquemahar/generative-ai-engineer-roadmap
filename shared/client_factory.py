import os
from dotenv import load_dotenv

load_dotenv()

def get_openai_client():
    """
    Returns an OpenAI-compatible client.
    Uses Azure AI Foundry if AZURE_PROJECT_ENDPOINT is set and accessible.
    Falls back to direct OpenAI if OPENAI_API_KEY is set.
    """
    azure_endpoint = os.environ.get("AZURE_PROJECT_ENDPOINT")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if openai_key:
        # Direct OpenAI — temporary 
        from openai import OpenAI
        print("Using: Openai API direct")
        return OpenAI(api_key=openai_key) , os.environ.get("OPENAI_MODEL", 'gpt-4.1-mini')
    elif azure_endpoint:
        # Azure AI Foundry — primary
        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectClient
        print("Using: Azure AI foundry")
        project_client = AIProjectClient(
            endpoint=azure_endpoint,
            credential=DefaultAzureCredential()
        )
        return project_client.get_openai_client(), os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5")
    else:
        raise ValueError(
            "No API credentials found. Set either OPENAI_API_KEY or AZURE_PROJECT_ENDPOINT"
        )