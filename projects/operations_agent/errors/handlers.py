# projects/operations_agent/errors/handlers.py
"""
Centralised handlers for all 6 failure modes.

Mode 1 — Timeout/retry:     RetryPolicy on nodes in agent_graph.py
Mode 2 — DB connection:     handle_db_error()
Mode 3 — Invalid tool args: ToolNode default (handle_tool_errors=True)
Mode 4 — Malformed LLM:     try/except in agent_node
Mode 5 — Duplicate action:  is_duplicate_action() in write_guard
Mode 6 — Approval rejected: log_rejection() in approval_node
"""
import sys
from pathlib import Path
from sqlalchemy.exc import OperationalError

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import AuditLog
# ── Mode 2 ────────────────────────────────────────────────────────────────

def handle_db_error(e: OperationalError, tool_name: str) -> dict:
    """Return a graceful error dict when the DB is unreachable."""
    return {
        "error": "Database temporarily unavailable. Please try again shortly.",
        "tool":  tool_name,
        "detail": str(e),   
    }

# ── Mode 5 ────────────────────────────────────────────────────────────────
def is_duplicate_action(action_id: str) -> bool:
    """
    Return True if this action_id already exists in the audit log.
    action_id is a UUID generated per approved action in approval_node.
    Keyed on a unique DB column — no JSON comparison, no float/int ambiguity.
    """
    if not action_id:
        return False
    with SessionLocal() as session:
        existing = session.query(AuditLog).filter(
            AuditLog.action_id == action_id
        ).first()
        return existing is not None

# ── Mode 6 ────────────────────────────────────────────────────────────────
def log_rejection(tool_name: str, tool_input: dict, reason: str = "rejected by operator") -> None:
    """Write a rejection entry to the audit log when a write tool is denied."""
    with SessionLocal() as session:
        session.add(AuditLog(
            action="rejected",
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output={"status": "rejected", "reason": reason}
        )) 
        session.commit()   
    