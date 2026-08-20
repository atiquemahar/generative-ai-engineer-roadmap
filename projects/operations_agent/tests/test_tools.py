# tests/test_tools.py
import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.tools.read_tools import (
    get_customer,
    get_order,
    get_shipment,
    check_inventory,
    get_refund_policy,
)

# ── get_customer ───────────────────────────────────────────────────────────

def test_get_customer_valid():
    result = get_customer.invoke({"customer_id": "C001"})
    assert result["name"] == "Alice Smith"
    assert result["tier"] == "premium"
    assert result["status"] == "active" 

def test_get_customer_suspended():
    result = get_customer.invoke({"customer_id": "C003"})
    assert result["status"] == "suspended"

def test_get_customer_invalid_id():
    with pytest.raises(ValueError, match="not found"):
        get_customer.invoke({"customer_id": "C999"})

def test_get_customer_empty_id():
    with pytest.raises(ValueError, match="not found"):
        get_customer.invoke({"customer_id": ""})

# ── get_order ──────────────────────────────────────────────────────────────

def test_get_order_valid():
    result = get_order.invoke({"order_id": "O001"})
    assert result["customer_id"] == "C001"
    assert result["status"] == "shipped"
    assert result["total_usd"] == 149.99

def test_get_order_processing():
    result = get_order.invoke({"order_id": "O002"})
    assert result["status"] == "processing"

def test_get_order_invalid_id():
    with pytest.raises(ValueError, match="not found"):
        get_order.invoke({"order_id": "O999"}) 

# ── get_shipment ───────────────────────────────────────────────────────────

def test_get_shipment_valid():
    result = get_shipment.invoke({"order_id": "O001"})
    assert result["carrier"] == "FedEx"
    assert result["status"] == "in_transit"
    assert "tracking_number" in result

def test_get_shipment_no_shipment_yet():
    # O002 exists as an order but has no shipment record (still processing)
    with pytest.raises(ValueError, match="No shipment record"):
        get_shipment.invoke({"order_id": "O002"})

def test_get_shipment_invalid_order():
    with pytest.raises(ValueError, match="not found"):
        get_shipment.invoke({"order_id": "O999"})

# ── check_inventory ────────────────────────────────────────────────────────

def test_check_inventory_in_stock():
    result = check_inventory.invoke({"product_id": "P001"})
    assert result["stock"] == 42
    assert result["product_name"] == "Wireless Headphones"

def test_check_inventory_out_of_stock():
    result = check_inventory.invoke({"product_id": "P002"})
    assert result["stock"] == 0          # out of stock — still a valid response

def test_check_inventory_invalid_id():
    with pytest.raises(ValueError, match="not found"):
        check_inventory.invoke({"product_id": "P999"})

# ── get_refund_policy ──────────────────────────────────────────────────────

def test_get_refund_policy_returns_string():
    result = get_refund_policy.invoke({})
    assert isinstance(result, str)
    assert len(result) > 0

def test_get_refund_policy_contains_key_terms():
    result = get_refund_policy.invoke({})
    assert "30 days" in result
    assert "500" in result              # approval threshold
    assert "non-refundable" in result