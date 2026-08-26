# experiments/day35_db_tools.py

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.database.seed import create_tables, seed_data
from projects.operations_agent.tools.db_tools import (
    get_customer_db, get_order_db, get_shipment_db,
    check_inventory_db, get_refund_policy_db
)
from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import AuditLog

# ── Setup ──────────────────────────────────────────────────────────────────
print("Setting up database...")
create_tables()
seed_data()

# ── Tests ──────────────────────────────────────────────────────────────────
print("\n" + "═"*55)
print("TEST 1 — get_customer_db: valid")
result = get_customer_db.invoke({"customer_id": "C001"})
print(f"  {result}")
assert result["name"] == "Alice Smith"
assert result["tier"] == "premium"

print("\nTEST 2 — get_customer_db: invalid")
try:
    get_customer_db.invoke({"customer_id": "C999"})
except ValueError as e:
    print(f"  ValueError: {e} ✓")

print("\nTEST 3 — get_order_db: valid")
result = get_order_db.invoke({"order_id": "O001"})
print(f"  {result}")
assert result["status"] == "shipped"
assert result["total_usd"] == 149.99

print("\nTEST 4 — get_shipment_db: in transit")
result = get_shipment_db.invoke({"order_id": "O001"})
print(f"  {result}")
assert result["carrier"] == "FedEx"
assert result["status"] == "in_transit"

print("\nTEST 5 — get_shipment_db: no shipment yet")
try:
    get_shipment_db.invoke({"order_id": "O002"})
except ValueError as e:
    print(f"  ValueError: {e} ✓")

print("\nTEST 6 — check_inventory_db: out of stock")
result = check_inventory_db.invoke({"product_id": "P002"})
print(f"  {result}")
assert result["stock"] == 0

print("\nTEST 7 — get_refund_policy_db")
result = get_refund_policy_db.invoke("")
print(f"  {result[:60]}...")
assert "30 days" in result

# ── Audit log check ────────────────────────────────────────────────────────
print("\n" + "═"*55)
print("TEST 8 — Audit log written to DB")
with SessionLocal() as session:
    logs = session.query(AuditLog).all()
    print(f"  Audit entries written: {len(logs)}")
    for log in logs:
        print(f"  [{log.tool_name}] input={log.tool_input} → output keys={list(log.tool_output.keys()) if log.tool_output else None}")
    assert len(logs) >= 5  # one per successful tool call

print("\n✓ All tests passed")
