import os
import time
from dotenv import load_dotenv
from openai import AzureOpenAI


load_dotenv()




def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

azure_endpoint = get_env("AZURE_OPENAI_ENDPOINT")
if azure_endpoint.endswith("/openai/v1"):
    azure_endpoint = azure_endpoint[: -len("/openai/v1")]

client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=get_env("OPENAI_API_KEY"),
    api_version="2024-02-01"
)

def call_model(prompt: str, system: str = "you are a helpful assistant"):
    deployment_name = get_env("AZURE_DEPLOYMENT_NAME")
    start = time.time()
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role" : "system", "content" : system},
            {"role" : "user", "content" : prompt}

        ],
        
    )
    latency = time.time() - start
    return {
        "content": response.choices[0].message.content,
        "tokens_prompts" : response.usage.prompt_tokens,
        "tokens_completion" : response.usage.completion_tokens,
        "tokens_total" : response.usage.total_tokens,
        "latency_seconds" : round(latency, 3)

    }

if __name__ == "__main__":
    result = call_model("what are the 3 main cloud providers?")
    output_path = os.path.join(os.path.dirname(__file__), "day01_results.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(result))
    print(f"Saved result to {output_path}")


