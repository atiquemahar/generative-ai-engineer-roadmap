# experiments/day32_tool_calling_agent.py
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import  HumanMessage

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.graph.agent_graph import graph
from projects.operations_agent.state import AgentState

def run(user_input: str, label:str):
    print(f"\n{'─'*60}")
    print(f"TEST: {label}")
    print(f"INPUT: {user_input}")
    print("─" * 60)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_input)],
        "customer_id": None,
        "customer_name": None,
        "order_id": None,
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

    for step in graph.stream(initial_state, stream_mode="updates"):
        node = list(step.keys())[0]
        msgs = step[node].get("messages", [])
        for msg in msgs:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  [{node}] → tool_call: {tc['name']}({tc['args']})")
            elif hasattr(msg, "content") and msg.content:
                print(f"  [{node}] → {msg.content}")
            elif hasattr(msg, "name"):
                print(f"  [tool result: {msg.name}] → {msg.content[:120]}")

# ── 3 test cases ───────────────────────────────────────────────────────────
run(
    "Where is order O001 for customer C001?",
    "Should call get_order AND get_shipment"
)

run(
    "What is the refund policy?",
    "Should call get_refund_policy only"
)

run(
    "Can you check the customer details?",
    "Missing customer_id — agent should ask for it"
)

