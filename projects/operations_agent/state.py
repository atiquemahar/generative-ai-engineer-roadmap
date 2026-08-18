# projects/operations-agent/state.py

from typing import TypedDict, Annotated, Optional
from operator import add
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Conversation
    messages: Annotated[list[AnyMessage], add_messages] # reducer: append, don't overwrite

    # Customer context (set once, never overwritten)
    customer_id: Optional[str]
    customer_name: Optional[str]

    # Active task context
    order_id: Optional[str]
    issue_category: Optional[str] # shipment_delay/refund/product_defect/account

    # Retrieved data (updated by tools)
    order_data: Optional[dict]
    shipment_data: Optional[dict]
    policy_evidence: Optional[dict]

    # Decision tracking
    proposed_action: Optional[str]
    approval_required: Optional[bool]
    approval_status: Optional[str] # pending/approved/rejected
    action_executed: Optional[bool]

    # Audit — reducers accumulate across nodes
    tool_calls_made: Annotated[list[str], add]
    errors: Annotated[list[str], add]

