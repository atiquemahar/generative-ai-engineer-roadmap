# experiments/day33_full_graph.py
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal
from langgraph.graph import START, END, StateGraph
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState
from projects.operations_agent.tools.read_tools import (
    get_customer, get_order, get_shipment, check_inventory, get_refund_policy
)

# ── LLM ───────────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2025-04-01-preview",
)

TOOLS = {
    "get_customer": get_customer,
    "get_order": get_order,
    "get_shipment": get_shipment,
    "check_inventory": check_inventory,
    "get_refund_policy": get_refund_policy,
}

# ══════════════════════════════════════════════════════════════════════════
# NODE 1 — understand_request
# Responsibility: classify the intent and extract any IDs from the message
# ══════════════════════════════════════════════════════════════════════════
def understand_request(state: AgentState) -> dict:
    last_msg = state["messages"][-1].content

    response = llm.invoke([
        SystemMessage(content=(
            "Extract intent and IDs from the customer message. "
            "Respond in this exact format (no extra text):\n"
            "INTENT: <one of: order_status, refund_policy, customer_info, inventory_check, unknown>\n"
            "CUSTOMER_ID: <id or NONE>\n"
            "ORDER_ID: <id or NONE>\n"
            "PRODUCT_ID: <id or NONE>"
        )),
        HumanMessage(content=last_msg)
    ])

    # Parse the structured response
    lines = response.content.strip().splitlines()
    parsed = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            parsed[k.strip()] = v.strip()

    intent = parsed.get("INTENT", "unknown") 
    cust_id = parsed.get("CUSTOMER_ID", "NONE") 
    order_id = parsed.get("ORDER_ID", "NONE")
    product_id = parsed.get("PRODUCT_ID", "NONE")
    # In understand_request, after parsing:    

    return {
        "issue_category": intent,
        "customer_id": None if cust_id == "NONE" else cust_id,
        "order_id": None if order_id == "NONE" else order_id,
        "product_id":  None if product_id == "NONE" else product_id,
        "tool_calls_made": ["understand_request"],
        "messages": [AIMessage(content=f"Intent: {intent}")]
    }  

# ══════════════════════════════════════════════════════════════════════════
# NODE 2 — validate_identity
# Responsibility: check we have the IDs required for the intent
# ══════════════════════════════════════════════════════════════════════════

def validate_identity(state: AgentState) -> dict:
    intent = state.get("issue_category", "unknown")
    cust_id = state.get("customer_id")
    order_id = state.get("order_id")

    missing = []
    if intent in ("order_status",)  and not order_id:
        missing.append("order ID")
    if intent in ("customer_info",)  and not cust_id:
        missing.append("customer ID")
    if intent == "inventory_check" and not state.get("product_id"):
        missing.append("product ID")    

    if missing:
        msg = f"To help with that I need your {' and '.join(missing)}. Could you provide it?"
        return {
            "proposed_action": "request_missing_info",
            "tool_calls_made": ["validate_identity"],
            "messages": [AIMessage(content=msg)]
        }
    return {
        "proposed_action": "proceed",
        "tool_calls_made": ["validate_identity"],
        "messages": [AIMessage(content="Identity validated — proceeding.")]
    }  
def route_after_validation(state: AgentState) -> Literal["select_tool", "formulate_response"]:
    if state.get("proposed_action")  == "request_missing_info":
        return "formulate_response"
    return "select_tool"

# ══════════════════════════════════════════════════════════════════════════
# NODE 3 — select_tool
# Responsibility: decide which tool(s) to call based on intent
# ══════════════════════════════════════════════════════════════════════════
INTENT_TO_TOOLS = {
    "order_status":    ["get_order", "get_shipment"],
    "refund_policy":   ["get_refund_policy"],
    "customer_info":   ["get_customer"],
    "inventory_check": ["check_inventory"],
    "unknown":         [],
}

def select_tool(state: AgentState) -> dict:
    intent = state.get("issue_category", "unknown")
    tools_needed = INTENT_TO_TOOLS.get(intent, [])
    return {
        "proposed_action": ",".join(tools_needed) if tools_needed else "none",
        "tool_calls_made": ["select_tool"],
    }

# ══════════════════════════════════════════════════════════════════════════
# NODE 4 — execute_tool
# Responsibility: call the selected tools and store results in state
# ══════════════════════════════════════════════════════════════════════════
def execute_tool(state: AgentState) -> dict:
    tools_to_run = [
        t.strip() for t in state.get("proposed_action", "").split(",")
        if t.strip() and t.strip() != "none"
    ]

    order_data = state.get("order_data")
    shipment_data = state.get("shipment_data")
    policy = state.get("policy_evidence")
    customer_data = state.get("order_data") # reuse order_data slot for customer
    errors = []

    for tool_name in tools_to_run:
        tool_fn = TOOLS.get(tool_name)
        if not tool_fn:
            errors.append(f"Unknown tool: {tool_name}")
            continue
        try:
            if tool_name == "get_order":
                order_data = tool_fn.invoke({"order_id": state["order_id"]})
            elif tool_name == "get_shipment":
                shipment_data = tool_fn.invoke({"order_id": state["order_id"]})
            elif tool_name == "get_customer":
                order_data = tool_fn.invoke({"customer_id": state["customer_id"]})
            elif tool_name == "check_inventory":
                pid = state.get("product_id")
                if not pid:
                    errors.append("check_inventory failed: no product_id in state")
                else:
                    order_data = tool_fn.invoke({"product_id": pid})
            elif tool_name == "get_refund_policy":
                policy = tool_fn.invoke("")
        except Exception as e:
            errors.append(f"{tool_name} failed: {str(e)}")       

    return {
    "order_data":      customer_data if customer_data and not order_data else order_data,
    "shipment_data":   shipment_data,
    "policy_evidence": {"text": policy} if isinstance(policy, str) else policy,
    "tool_calls_made": tools_to_run,
    "errors":          errors,
    }                      

# ══════════════════════════════════════════════════════════════════════════
# NODE 5 — determine_next
# Responsibility: decide whether we have enough to answer or need to retry
# ══════════════════════════════════════════════════════════════════════════
def determine_next(state: AgentState) -> dict:
    errors = state.get("errors", [])
    if errors:
        return {
            "proposed_action": "error",
            "tool_calls_made": ["determine_next"],
        }
    return {
        "proposed_action": "respond",
        "tool_calls_made": ["determine_next"],
    }

def route_after_determine(state: AgentState) -> Literal["formulate_response"]: 
    return "formulate_response" # always goes to formulate — errors handled there

# ══════════════════════════════════════════════════════════════════════════
# NODE 6 — formulate_response
# Responsibility: compose the final customer-facing reply from state data
# ══════════════════════════════════════════════════════════════════════════
def formulate_response(state: AgentState) -> dict:
    # If we hit errors, say so clearly
    if state.get("errors"):
        error_msg = "; ".join(state["errors"])
        return {
            "action_executed": False,
            "tool_calls_made": ["formulate_response"],
            "messages": [AIMessage(content=f"I wasn't able to complete that request: {error_msg}")]
        }

    # If we were waiting for missing info, the message is already in state
    if state.get("proposed_action") == "request_missing_info":
        return {
            "action_executed": False,
            "tool_calls_made": ["formulate_response"],
        }

    # Build context from whatever was retrieved
    context_parts = []
    if state.get("order_data"):
        context_parts.append(f"Order data: {state['order_data']}")
    if state.get("shipment_data"):
        context_parts.append(f"Shipment data: {state['shipment_data']}")
    if state.get("policy_evidence"):
        context_parts.append(f"Policy: {state['policy_evidence']}")

    if not context_parts:
        return {
            "action_executed": False,
            "tool_calls_made": ["formulate_response"],
            "messages": [AIMessage(content="I don't have enough information to answer that. Could you give me more detail?")]
        }
    
    context = "\n".join(context_parts)
    original_question = state["messages"][0].content 

    response = llm.invoke([
        SystemMessage(content=(
            "You are a customer operations assistant. "
            "Using ONLY the data provided below, write a clear, concise response "
            "to the customer's question. Do not guess or add information not in the data."
        )),
        HumanMessage(content=f"Question: {original_question}\n\nData:\n{context}")
    ])

    return {
        "action_executed": True,
        "tool_calls_made": ["formulate_response"],
        "messages": [AIMessage(content=response.content)]
    } 

# ══════════════════════════════════════════════════════════════════════════
# BUILD GRAPH
# ══════════════════════════════════════════════════════════════════════════

builder =  StateGraph(AgentState) 

builder.add_node("understand_request", understand_request)
builder.add_node("validate_identity", validate_identity)
builder.add_node("select_tool", select_tool)
builder.add_node("execute_tool", execute_tool)
builder.add_node("determine_next", determine_next)
builder.add_node("formulate_response", formulate_response)

builder.add_edge(START,     "understand_request")
builder.add_edge("understand_request",  "validate_identity")
builder.add_conditional_edges("validate_identity",  route_after_validation)
builder.add_edge("select_tool", "execute_tool")
builder.add_edge("execute_tool", "determine_next")
builder.add_conditional_edges("determine_next", route_after_determine)
builder.add_edge("formulate_response", END)

graph = builder.compile()

# ══════════════════════════════════════════════════════════════════════════
# 10 TEST CASES
# ══════════════════════════════════════════════════════════════════════════

def run(user_input: str, label: str):
    print(f"\n{'═'*65}")
    print(f"TEST : {label}")
    print(f"INPUT: {user_input}")
    print("═" * 65)

    state: AgentState = {
        "messages":        [HumanMessage(content=user_input)],
        "customer_id":     None,
        "customer_name":   None,
        "product_id":      None,
        "order_id":        None,
        "issue_category":  None,
        "order_data":      None,
        "shipment_data":   None,
        "policy_evidence": None,
        "proposed_action": None,
        "approval_required": None,
        "approval_status": None,
        "action_executed": None,
        "tool_calls_made": [],
        "errors":          [],
    }

    for step in graph.stream(state, stream_mode="updates"):
        node = list(step.keys())[0]
        node_state = step[node]
        msgs = node_state.get("messages", [])
        tools_run = node_state.get("tool_calls_made", [])
        errors = node_state.get("errors", [])

        for msg in msgs:
            if hasattr(msg, "content") and msg.content:
                content = msg.content
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"  [{node}] {content}")
        if tools_run:
            print(f"  [{node}] tools: {tools_run}")
        if errors:
            print(f"  [{node}] errors: {errors}")

tests = [
    ("Where is order O001?",                              "order_status — has order ID"),
    ("Where is order O003?",                              "order_status — delivered order"),
    ("Where is order O999?",                              "order_status — invalid order ID"),
    ("What is the refund policy?",                        "refund_policy — no IDs needed"),
    ("Can you refund order O002?",                        "refund — order exists, no shipment"),
    ("Get details for customer C001",                     "customer_info — valid customer"),
    ("Get details for customer C999",                     "customer_info — invalid customer"),
    ("Check inventory for product P002",                  "inventory — out of stock"),
    ("Can you check the order?",                          "order_status — missing order ID"),
    ("Tell me something about the weather",               "unknown intent"),
]

for user_input, label in tests:
    run(user_input, label) 
