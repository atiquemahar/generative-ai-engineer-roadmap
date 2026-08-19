# experiments/day30_conditional_routing.py

from typing import Literal
from langgraph.graph import StateGraph, START, END
from openai import AzureOpenAI
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential



REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState   

load_dotenv()

#credential = DefaultAzureCredential()
#project_client = AIProjectClient(
    #endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    #credential=credential,
#)
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview"
)

MODEL = os.environ["MODEL_DEPLOYMENT_NAME"]

# ── Node 1: Classify issue category ───────────────────────────────────────
def classfiy_node(state: AgentState) -> dict:
    last_msg = state["messages"][-1].content
    response = client.responses.create(
        model=MODEL,
        instructions=(
            "Classify the customer issue into exactly one category. "
            "Return only the category word, nothing else.\n"
            "Categories: shipment_delay, refund_request, product_defect, account_issue, general"
        ),
        input=last_msg,
        max_output_tokens=300,
    )
    if response.output_text:
        category = response.output_text.strip().lower()
    else:
    # Extract from output content blocks
        category = response.output[0].content[0].text.strip().lower()
       
    # Guard: if LLM returns something unexpected, fall back to general
    valid = {"shipment_delay", "refund_request", "product_defect", "account_issue", "general"}
    if category not in valid:
        category = "general"
    return {
        "issue_category": category,
        "tool_calls_made": ["classify_issue"]
    }

# ── Router function ────────────────────────────────────────────────────────
def determine_route(state: AgentState) -> Literal[
    "check_shipment", "check_refund_eligibility",
    "check_defect_policy", "check_account", "general_response"
]:
    routes = {
        "shipment_delay":  "check_shipment",
        "refund_request":  "check_refund_eligibility",
        "product_defect":  "check_defect_policy",
        "account_issue":   "check_account",
        "general":         "general_response",
    }
    return routes.get(state["issue_category"] or "general", "general_response")

# ── Route nodes ────────────────────────────────────────────────────────────
from langchain_core.messages import AIMessage
def check_shipment(state: AgentState) -> dict:
    return {
        "proposed_action": "fetch shipment tracking data",
        "tool_calls_made": ["check_shipment"],
        "messages": [AIMessage(content = f"Checking shipment status for order {state['order_id'] or 'unknown'}.")]
    }

def check_refund_eligibility(state: AgentState) -> dict:
    return {
        "proposed_action": "check refund policy eligibility",
        "approval_required": True,
        "approval_status": "pending",
        "tool_calls_made": ["check_refund_eligibility"],
        "messages": [AIMessage(content= "Checking refund eligibility against policy.")]
    }

def check_defect_policy(state: AgentState) -> dict:
    return {
        "proposed_action": "retrieve product defect policy",
        "tool_calls_made": ["check_defect_policy"],
        "messages": [AIMessage(content="Retrieving product defect and warranty policy.")]
    }

def check_account(state: AgentState) -> dict:
    return {
        "proposed_action": "look up account details",
        "tool_calls_made": ["check_account"],
        "messages": [AIMessage(content= "Looking up account information.")]
    }

def general_response(state: AgentState) -> dict:
    return {
        "proposed_action": "provide general assistance",
        "tool_calls_made": ["general_response"],
        "messages": [AIMessage(content="I can help with that. Could you give me more detail?")]
    }

# ── Build graph ────────────────────────────────────────────────────────────

builder = StateGraph(AgentState)

builder.add_node("classify", classfiy_node)
builder.add_node("check_shipment", check_shipment)
builder.add_node("check_refund_eligibility", check_refund_eligibility)
builder.add_node("check_defect_policy", check_defect_policy)
builder.add_node("general_response", general_response)
builder.add_node("check_account", check_account)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", determine_route)
builder.add_edge("check_shipment", END)
builder.add_edge("check_refund_eligibility", END)
builder.add_edge("check_defect_policy", END)
builder.add_edge("check_account", END)
builder.add_edge("general_response", END)

graph = builder.compile()

# ── 8 test cases ───────────────────────────────────────────────────────────
from langchain_core.messages import HumanMessage

test_cases = [
    # (input,                                         expected_route)
    ("My package hasn't arrived in 2 weeks",          "check_shipment"),
    ("Where is my order O-789?",                      "check_shipment"),
    ("I want a refund for my last purchase",          "check_refund_eligibility"),
    ("The product arrived broken",                    "check_defect_policy"),
    ("Item is defective, screen is cracked",          "check_defect_policy"),
    ("I can't log into my account",                   "check_account"),
    ("What are your business hours?",                 "general_response"),
    ("",                                              "general_response"),   # edge case: empty input
]

print(f"{'INPUT':<45} {'CATEGORY':<20} {'ROUTE':<30} {'PASS'}")
print("-" * 105)

passed = 0
for user_input, expected_route in test_cases:
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_input or "hello")],
        "customer_id": "CUST-TEST",
        "customer_name": "Test User",
        "order_id": "O-789",
        "issue_category": None,
        "order_data": None,
        "shipment_data": None,
        "policy_evidence": None,
        "proposed_action": None,
        "approval_required": None,
        "approval_status": None,
        "action_executed": None,
        "tool_calls_made": [],
        "errors": [],
    }

    result = graph.invoke(initial_state)
    category = result["issue_category"]
    actual_route = result["tool_calls_made"][-1]

    ok = "✓" if actual_route == expected_route else "✗"
    if actual_route == expected_route:
        passed += 1

    label = (user_input[:42] + "...") if len(user_input) > 42 else user_input
    print(f"{label:<45} {category:<20} {actual_route:<30} {ok}")

print(f"\nResult: {passed}/{len(test_cases)} passed")