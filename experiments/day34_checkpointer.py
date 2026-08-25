# experiments/day34_checkpointer.py

import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from projects.operations_agent.graph.agent_graph import builder # reuse Day 32 graph
from projects.operations_agent.state import AgentState

# ── Compile with checkpointer ─────────────────────────────────────────────
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

def run_turn(user_input: str, config: dict, turn_label: str):
    print(f"\n  [{turn_label}] USER: {user_input}")
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config
    )
    last_msg = result["messages"][-1].content
    if len(last_msg) > 200:
        last_msg = last_msg[:200] + "..."
    print(f"  [{turn_label}] AGENT: {last_msg}")
    return result
def print_state(config: dict, label: str):
    state = graph.get_state(config)
    v = state.values
    print(f"\n  [STATE — {label}]")
    print(f"    messages count:  {len(v.get('messages', []))}  ← grows each turn = persistence working")
    print(f"    customer_id:     {v.get('customer_id')}  ← None: Day32 graph doesn't write this field")
    print(f"    tool_calls_made: {v.get('tool_calls_made')}")
    # Show last message to prove continuity
    msgs = v.get("messages", [])
    if msgs:
        last = msgs[-1]
        print(f"    last message:    [{last.__class__.__name__}] {str(last.content)[:80]}")

# ══════════════════════════════════════════════════════════════════════════
# TEST 1 — State persists across 3 turns in the same thread
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "═"*65)
print("TEST 1: Multi-turn — same thread_id, state persists")
print("═"*65)

config_A = {"configurable": {"thread_id": "session-001"}}

run_turn("Where is order O001?", config_A, "Turn 1")
print_state(config_A, "after Turn 1")

run_turn("What is the refund policy?", config_A, "Turn 2")
print_state(config_A, "after Turn 2")

run_turn("Get details for customer C001", config_A, "Turn 3")
print_state(config_A, "after Turn 3 — customer_id should be C001")

# ══════════════════════════════════════════════════════════════════════════
# TEST 2 — Different thread_id → fresh state
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "═"*65)
print("TEST 2: Different thread_id → fresh state")
print("═"*65)

config_B = {"configurable": {"thread_id": "session-002"}}

run_turn("Where is order O001?", config_B, "Turn 1 thread-B")
print_state(config_B, "thread-B — independent from thread-A")

# Verify thread A state is unchanged
print_state(config_A, "thread-A — should still have C001 from Test 1")

# ══════════════════════════════════════════════════════════════════════════
# TEST 3 — Inspect checkpoint history
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "═"*65)
print("TEST 3: Checkpoint history for thread-A")
print("═"*65)

history = list(graph.get_state_history(config_A))
print(f"  Total checkpoints saved: {len(history)}")
print(f"  Most recent checkpoint ID: {history[0].config['configurable'].get('checkpoint_id', 'n/a')}")
print(f"  Oldest checkpoint ID:      {history[-1].config['configurable'].get('checkpoint_id', 'n/a')}")
