# projects/operations_agent/graph/agent_graph.py
import sys, os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState
from projects.operations_agent.tools.db_tools import (
    get_customer_db, 
    get_order_db, 
    get_shipment_db,
    check_inventory_db, 
    get_refund_policy_db
)
from projects.operations_agent.tools.write_tools import (
    issue_refund, 
    create_support_ticket
)

# ── Tool lists ─────────────────────────────────────────────────────────────
READ_TOOLS = [get_customer_db, get_order_db, get_shipment_db,
              check_inventory_db, get_refund_policy_db]

WRITE_TOOLS = [issue_refund, create_support_ticket]

WRITE_TOOL_NAMES = [t.name for t in WRITE_TOOLS]

ALL_TOOLS = WRITE_TOOLS + READ_TOOLS
# ── LLM  ────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2025-04-01-preview",
)

llm_with_tools = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = (
    "You are a customer operations assistant. "
    "Use tools to look up customer, order, shipment, and inventory data. "
    "Never guess IDs or details — always retrieve first. "
    "For refunds and support tickets, call the appropriate write tool. "
    "The system will handle human approval before the action executes. "
    "If an action is rejected, acknowledge it and ask how else you can help."
)

# ── Nodes ──────────────────────────────────────────────────────────────────
def agent_node(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def approval_node(state: AgentState) -> Command[Literal["write_tools", "agent_node"]]:
    """
    Pause here and ask a human to approve or reject the pending write tool call.

    First invoke:  interrupt() raises a special exception → graph saves state → pauses.
    Resume invoke: interrupt() returns the value passed to Command(resume=...).
                   True  → route to write_tools (tool executes).
                   False → inject rejection ToolMessage → route back to agent_node.
    """
    last_msg = state["messages"][-1]
    tool_call = last_msg.tool_calls[0]

    # ── PAUSE ────────────────────────────────────────────────────────────
    approved = interrupt({
        "tool":     tool_call["name"],
        "args":     tool_call["args"],
        "question": (
            f"Approve  '{tool_call['name']}' "
            f"with args {tool_call['args']}? "
            f"Reply True to approve, False to reject."
        ),
    })
    # ── RESUME ───────────────────────────────────────────────────────────

    if approved:
        return Command(goto="write_tools")

    # Rejected: give the agent a ToolMessage so the conversation stays valid
    rejection_msg = ToolMessage(
        content=(
            f"Action '{tool_call['name']}' was rejected by the human operator. "
            "Do not retry. Inform the customer and offer alternatives."
        ),
        tool_call_id = tool_call["id"],
    )
    return Command(
        update={
            "messages":     [rejection_msg],
            "approval_status":  "rejected",
        },
        goto="agent_node"
    )


def route_from_agent(state: AgentState) -> str:
    """Route to approval gate, read tools, or END based on what the agent called."""
    last_msg = state["messages"][-1]
    if not last_msg.tool_calls:
        return END
    tool_name = last_msg.tool_calls[0]["name"]
    if tool_name in WRITE_TOOL_NAMES:
        return "approve_node"
    return "read_tools"



read_tool_node = ToolNode(READ_TOOLS)
write_tool_node = ToolNode(WRITE_TOOLS)

# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(AgentState)
builder.add_node("agent_node", agent_node)
builder.add_node("approve_node", approval_node)
builder.add_node("read_tools", read_tool_node)
builder.add_node("write_tools", write_tool_node)

builder.add_edge(START, "agent_node")
builder.add_conditional_edges("agent_node", route_from_agent)
builder.add_edge("read_tools", "agent_node")
builder.add_edge("write_tools", "agent_node")

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

