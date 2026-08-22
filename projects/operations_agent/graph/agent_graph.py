# projects/operations_agent/graph/agent_graph.py
import sys, os
from pathlib import Path
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.state import AgentState
from projects.operations_agent.tools.read_tools import (
    get_customer,
    get_order,
    get_shipment,
    check_inventory,
    get_refund_policy
)

# ── LLM + tools ────────────────────────────────────────────────────────────
tools = [get_customer, get_order, get_shipment, check_inventory, get_refund_policy]

llm = AzureChatOpenAI(
    azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2025-04-01-preview",
)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = (
    "You are a customer operations assistant. "
    "Use the available tools to look up customer, order, shipment, "
    "and inventory information. "
    "Always retrieve data before answering — never guess IDs or details. "
    "If you do not have enough information to call a tool, ask the user."
)

# ── Nodes ──────────────────────────────────────────────────────────────────
def agent_node(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END

tool_node = ToolNode(tools)

# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(AgentState)
builder.add_node("agent_node", agent_node)
builder.add_node("tools", tool_node)
builder.add_edge(START, "agent_node")
builder.add_conditional_edges("agent_node", should_continue)
builder.add_edge("tools", "agent_node")

graph = builder.compile()

