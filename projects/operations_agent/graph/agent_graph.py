# projects/operations_agent/graph/agent_graph.py
import sys, os, uuid, json
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command, RetryPolicy
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState
from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import AuditLog
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
from projects.operations_agent.errors.handlers import (
    is_duplicate_action,
    log_rejection
)

# ── Tool lists ─────────────────────────────────────────────────────────────
READ_TOOLS = [get_customer_db, get_order_db, get_shipment_db,
              check_inventory_db, get_refund_policy_db]

WRITE_TOOLS = [issue_refund, create_support_ticket]

# Registry for direct invocation inside write_guard
WRITE_TOOLS_MAP = {t.name: t for t in WRITE_TOOLS}

WRITE_TOOL_NAMES = set(WRITE_TOOLS_MAP.keys())

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
    # Mode 4: malformed/failed LLM response
    try:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    except Exception as e:
        fallback = AIMessage(
            content=(
                "I'm having trouble processing your request right now. "
                "A human agent will follow up with you shortly."
            )
        )
        return {
            "messages":         [fallback],
            "errors":           [f"agent_node failed: {type(e).__name__}: {str(e)}"],
            "approval_required": True,
        }

def approval_node(state: AgentState) -> Command[Literal["write_guard", "agent_node"]]:
    """
    Pause for human approval. On approve: generate action_id UUID and route to
    write_guard. On reject: log rejection and route back to agent_node.
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
        return Command(
            update={"action_id": str(uuid.uuid4())},  # UUID generated here
            goto="write_guard"
        )

    # Mode 6: log rejection before routing away
    log_rejection(
        tool_name=tool_call["name"],
        tool_input=tool_call["args"],
        reason="rejected by human operator",
    )

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

def write_guard(state: AgentState) -> dict:
    """
    Production-grade write gate. Three responsibilities:
      1. Idempotency check — action_id must not already exist in audit_logs.
      2. Tool execution   — calls write tool directly (not via ToolNode).
      3. Audit logging    — writes result + action_id to audit_logs.

    write_guard is the only node that writes to audit_logs for write actions.
    write_tools.py contains business logic only.
    """
    action_id = state.get("action_id")
    last_msg = state["messages"][-1]
    tool_call = last_msg.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    # ── 1. Idempotency check ──────────────────────────────────────────────
    if is_duplicate_action(action_id):
        duplicate_msg = ToolMessage(
            content=(
                f"Action '{tool_name}' was already executed "
                f"(action_id={action_id}). Skipping duplicate."
            ),
            tool_call_id = tool_call["id"]
        )
        return Command(
            update={
                "messages":  [duplicate_msg],
                "action_id": None,          # clear after use
            },
            goto="agent_node"
        )

    # ── 2. Execute tool directly ──────────────────────────────────────────
    tool_fn = WRITE_TOOLS_MAP[tool_name]
    try:
        result = tool_fn.invoke(tool_args)
    except Exception as e:
        error_msg = ToolMessage(
            content=f"Tool '{tool_name}' failed: {str(e)}",
            tool_call_id = tool_call["id"]
        ) 
        return Command(
            update={
                "messages":  [error_msg],
                "errors":    [f"write_guard: {tool_name} raised {type(e).__name__}: {str(e)}"],
                "action_id": None,
            },
            goto="agent_node",
        ) 

    # ── 3. Audit log with action_id ───────────────────────────────────────
    with SessionLocal() as session:
        session.add(AuditLog(
            action_id=action_id,
            action=f"{tool_name}_executed",
            tool_name=tool_name,
            tool_input=tool_args,
            tool_output=result,
        ))
        session.commit()

    success_msg = ToolMessage(
        content=json.dumps(result),
        tool_call_id=tool_call["id"],
    )
    return Command(
        update={
            "messages":        [success_msg],
            "action_id":       None,        # clear after use
            "action_executed": True,
            "approval_status": "approved",
        },
        goto="agent_node",
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



read_tool_node = ToolNode(READ_TOOLS, handle_tool_errors=True)


# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(AgentState)

builder.add_node("agent_node", agent_node)
builder.add_node("approve_node", approval_node)
builder.add_node("write_guard", write_guard)
builder.add_node(
    "read_tools",
    read_tool_node,
    retry_policy=RetryPolicy(max_attempts=2, initial_interval=0.5),
)

builder.add_edge(START, "agent_node")
builder.add_conditional_edges("agent_node", route_from_agent)
builder.add_edge("read_tools", "agent_node")
builder.add_edge("write_guard", "agent_node")

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

