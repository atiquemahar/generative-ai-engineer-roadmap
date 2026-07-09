import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

def get_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

def get_project_client() -> AIProjectClient:
    """
    FastAPI will execute this function to create the client 
    and pass it down to your route.
    """
    client = AIProjectClient(
        endpoint=os.environ["AZURE_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential()
    )

    return client