import os
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient



load_dotenv()

credential = DefaultAzureCredential()
project_endpoint = os.environ.get("AZURE_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT_NAME")




project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)



def call_model(prompt: str, system: str = "you are a helpful assistant") -> dict:
    """
    calls the model using OpenAI responses API
    and returns content, token counts and latency
    """
    start = time.time()
    with project_client.get_openai_client() as client:
        response = client.responses.create(
            model=MODEL_DEPLOYMENT,
            instructions=system,
            input=prompt
        
        )

    latency = time.time() - start

    return {
        "content": response.output_text,
        "tokens_input" : response.usage.input_tokens,
        "tokens_output" : response.usage.output_tokens,
        "tokens_total" : response.usage.total_tokens,
        "latency_seconds" : round(latency, 3)

    }

if __name__ == "__main__":
    result = call_model("what is Azure AI Foundry and what problems does it solve?")

    output_path = os.path.join(os.path.dirname(__file__), "day01_results.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for key, value in result.items():
            f.write(f"{key}: {value}\n")

    print("Results:")
    for key, value in result.items():
        print(f"{key}: {value}")


