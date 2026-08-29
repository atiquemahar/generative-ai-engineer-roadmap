# experiments/day36_human_approval.py
"""
Day 36 — Human approval gate using interrupt().

Three tests:
  1. Approve path  — write tool executes, audit log written.
  2. Reject path   — write tool never runs, agent responds gracefully.
  3. Audit log     — confirm only approved actions appear in DB.
"""
import sys
from pathlib import Path
from langgraph.types import Command
from langchain_core.messages import HumanMessage

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.database.seed import create_tables, seed_data
from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import AuditLog
from projects.operations_agent.graph.agent_graph import graph

# ── Setup ─────────────────────────────────────────────────────────────────

create_tables()
seed_data()

EMPTY_STATE = {
    "messages":        [],
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

# ── Test 1: Approve path ──────────────────────────────────────────────────

print("\n" + "═" * 60)
print("TEST 1: issue_refund — APPROVED")

config_1 = {"configurable": {"thread_id": "day36-approve-001"}}

initial_1 = {
    **EMPTY_STATE,
    "messages": [HumanMessage(
        content="Issue a $50 refund for order O001. Customer received a damaged item."
    )],
}

# First invoke — graph runs until interrupt() inside approval_node
result_1 = graph.invoke(initial_1, config_1)

# Inspect what was interrupted
state_1 = graph.get_state(config_1)
print(f"  Graph paused at:   {state_1.next}")
print(f"  Interrupt payload: {result_1.get('__interrupt__')}")

# Human approves — resume with True
print("  → Operator approves. Resuming...")
final_1 = graph.invoke(Command(resume=True), config_1)
print(f"  Agent reply: {final_1['messages'][-1].content[:120]}")

# ── Test 2: Reject path ───────────────────────────────────────────────────

print("\n" + "═" * 60)
print("TEST 2: create_support_ticket — REJECTED")

config_2 = {"configurable": {"thread_id": "day36-reject-001"}}

initial_2 = {
    **EMPTY_STATE,
    "messages": [HumanMessage(
        content="Create a high-priority support ticket for customer C001 — cannot log in."
    )],
}

# First invoke — pauses at interrupt()
graph.invoke(initial_2, config_2)

state_2 = graph.get_state(config_2)
print(f"  Graph paused at: {state_2.next}")

# Human rejects — resume with False
print("  → Operator rejects. Resuming...")
final_2 = graph.invoke(Command(resume=False), config_2)
print(f"  Agent reply: {final_2['messages'][-1].content[:120]}")

# Confirm write tool never fired — no ticket_created in audit log for this thread
with SessionLocal() as session:
    ticket_logs = (
        session.query(AuditLog)
        .filter(AuditLog.action == "ticket_created")
        .all()
    )
    print(f"  ticket_created audit entries: {len(ticket_logs)}  (expected 0)")

# ── Test 3: Audit log ─────────────────────────────────────────────────────

print("\n" + "═" * 60)
print("TEST 3: Audit log entries")

with SessionLocal() as session:
    logs = session.query(AuditLog).all()
    print(f"  Total entries: {len(logs)}")
    for log in logs:
        print(f"  [{log.action:20s}] tool={log.tool_name}  input={log.tool_input}")

print("\n✓ Day 36 complete")


