# shared/client_factory.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_openai_client():
    """Returns (client, model_name) for Azure AI Foundry."""
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    project_client = AIProjectClient(
        endpoint=os.environ["AZURE_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential()
    )
    return project_client.get_openai_client()