
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai import AzureOpenAI



load_dotenv()

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview"
)
MODEL = os.environ["MODEL_DEPLOYMENT_NAME"]



# step 1 define state

class RequestState(TypedDict):
    user_input: str
    category: str
    response: str

# Step 2: Write node functions (plain Python functions)
def classfiy_node(state: RequestState) -> dict:
    # Call LLM using AIProjectClient + responses.create()
    # NOT AzureOpenAI, NOT chat.completions.create()
    
    response = client.responses.create(
        model=MODEL,
        instructions="Classify the user request as one of: order, refund, general. Return only the category word.",
        input=state["user_input"],
        max_output_tokens=100,
        )
    return {"category": response.output_text.strip().lower()}

def order_node(state: RequestState) -> dict:
    return {"response": f"Handling order query: {state['user_input']}"}

def refund_node(state: RequestState) -> dict:
    return {"response": f"Handling refund query: {state['user_input']}"}

def general_node(state: RequestState) -> dict:
    return {"response": f"General response to: {state['user_input']}"}

# Step 3: Define routing
def route_by_category(state: RequestState) -> Literal["order", "refund", "general"]:
    return state["category"]

# Step 4: Build graph
builder = StateGraph(RequestState)
builder.add_node("classify", classfiy_node)
builder.add_node("order", order_node)
builder.add_node("refund", refund_node)
builder.add_node("general", general_node)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route_by_category)
builder.add_edge("order", END)
builder.add_edge("refund", END)
builder.add_edge("general", END)

graph = builder.compile()

# Step 5: Run it
# Add this at the bottom of the file, replace the invoke call
test_inputs = [
    "Where is my order O123?",           # → order
    "I want a refund for my purchase",   # → refund
    "What are your business hours?",     # → general
    "My package hasn't arrived yet",     # → order
    "Can I return this item?",           # → refund
]

for user_input in test_inputs:
    print(f"\nInput: {user_input}")
    for step in graph.stream(
        {"user_input": user_input, "category": "", "response": ""},
        stream_mode="updates"
    ):
        node_name = list(step.keys())[0]
        print(f"  [{node_name}] → {step[node_name]}")
   
    
