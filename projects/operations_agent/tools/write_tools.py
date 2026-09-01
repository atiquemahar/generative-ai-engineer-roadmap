# projects/operations_agent/tools/write_tools.py
import sys
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import AuditLog

# ── Input schemas ─────────────────────────────────────────────────────────
class IssueRefundInput(BaseModel):
    order_id: str = Field(description="Order ID starting with O, e.g. O001")
    amount: float = Field(description="Refund amount in USD. Must be positive.")
    reason: str   = Field(description="Reason for the refund.")

class CreateTicketInput(BaseModel):
    customer_id: str = Field(description="Customer ID starting with C")
    issue: str = Field(description="Description of the issue")
    priority: str = Field(description="Priority: low, medium, high")

# ── Write tools — business logic only ─────────────────────────────────────
# AuditLog writing and idempotency are handled by write_guard in agent_graph.py.
# These tools do one thing: validate inputs and return a result dict.

@tool("issue_refund", args_schema=IssueRefundInput)
def issue_refund(order_id: str, amount: float, reason: str) -> dict:
    """
    Issue a refund for a customer order.
    Requires human approval before this tool runs — approval is handled by the graph.
    """

    if amount <= 0:
        raise ValueError("Refund amount must be positive.")

    return  {
        "order_id": order_id,
        "amount_usd": amount,
        "reason": reason,
        "status": "refund_issued",
    }

@tool("create_support_ticket", args_schema=CreateTicketInput)
def create_support_ticket(customer_id: str, issue: str, priority: str) -> dict:
    """
    Create a support ticket for a customer.
    Requires human approval before this tool runs — approval is handled by the graph.
    """
    valid_priorities = {"low", "medium", "high"}
    if priority not in valid_priorities:
        raise ValueError(f"Priority must be one of {valid_priorities}. Got: '{priority}")

    ticket_id = f"TK-{customer_id}-001"
    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "priority": priority,
        "status": "ticket_created",
    }