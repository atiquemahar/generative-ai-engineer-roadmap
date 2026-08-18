# experiments/day29_state_test.py
from langchain_core.messages import HumanMessage, AIMessage
import sys
from pathlib import Path
from langgraph.graph.message import add_messages
from operator import add

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState

# ── Test 1: partial instantiation ─────────────────────────────────────────
# Only provide what's known at session start — everything else is None
initial_state: AgentState = {
    "messages": [],
    "customer_id": "CUST-001",
    "customer_name": "Ahmed",
    "order_id": None,
    "issue_category": None,
    "order_data": None,
    "shipment_data": None,
    "policy_evidence": None,
    "proposed_action": None,
    "approval_required": None,
    "approval_status": None,
    "action_executed": None,
    "tool_calls_made": None,
    "errors": [],
}

print("Test 1 — partial state:", initial_state["customer_name"], "| order_id:", initial_state["order_id"])

# ── Test 2: add_messages appends, not overwrites ───────────────────────────

msgs_v1 = [HumanMessage(content="Where is my order?")]
msgs_v2 = [AIMessage(content="Let me check that for you.")]

result = add_messages(msgs_v1, msgs_v2)
print("\nTest 2 — add_messages:")
print(f"  Input 1: {len(msgs_v1)} message")
print(f"  Input 2: {len(msgs_v2)} message")
print(f"  Result:  {len(result)} messages")  # expect 2
for m in result:
    print(f"    [{m.__class__.__name__}] {m.content}")

# ── Test 3: add_messages deduplicates by ID ────────────────────────────────
msg_a = HumanMessage(content="Original", id="msg-1")
msg_b = HumanMessage(content="Corrected", id="msg-1")  # same ID

result_dedup = add_messages([msg_a], [msg_b])
print("\nTest 3 — deduplication by ID:")
print(f"  Result count: {len(result_dedup)}")       # expect 1
print(f"  Content: {result_dedup[0].content}")      # expect "Corrected"

# ── Test 4: operator.add accumulates tool_calls_made ──────────────────────

calls_after_tool_1 = add([], ["fetch_order"])
calls_after_tool_2 = add(calls_after_tool_1, ["fetch_shipment"])
calls_after_tool_3 = add(calls_after_tool_2, ["retrieve_policy"])

print("\nTest 4 — tool_calls_made accumulation:")
print(f"  {calls_after_tool_3}")  # expect all 3 entries

