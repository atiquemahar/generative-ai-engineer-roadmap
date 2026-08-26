# projects/operations_agent/tools/db_tools.py

import os, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from projects.operations_agent.database.engine import SessionLocal
from projects.operations_agent.database.models import (
    Customer, Order, Shipment, Inventory, AuditLog
)

# ── Input schemas (same as read_tools.py) ─────────────────────────────────

class CustomerInput(BaseModel):
    customer_id: str = Field(description="Customer ID starting with C, e.g. C001")

class OrderInput(BaseModel):
    order_id: str = Field("Order ID starting with O, e.g. O001")

class InventoryInput(BaseModel):
    product_id: str = Field(description="Product ID starting with P, e.g. P001")

# ── Helper ────────────────────────────────────────────────────────────────

def _log(session: Session, action: str, tool_name: str, 
         tool_input: dict, tool_output: dict, customer_id: str = None):
    session.add(AuditLog(
        action=action,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        customer_id=customer_id,
    ))

# ── DB-backed tools ───────────────────────────────────────────────────────

@tool("get_customer_db", args_schema=CustomerInput)
def get_customer_db(customer_id: str) -> dict:
    """Retrieve customer information from database by ID."""
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")
        result = {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "tier": customer.tier,
            "status": customer.status,
        }
        _log(session, "lookup", "get_customer_db",
             {"customer_id": customer_id}, result, customer_id)
        session.commit
        return result

@tool("get_order_db", args_schema=OrderInput)
def get_order_db(order_id: str) -> dict:
    """Retrieve order details from database by order ID."""
    with SessionLocal() as session:
        order = session.get(Order, order_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found.")
        result = {
            "id": order.id,
            "customer_id": order.customer_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "status": order.status,
            "total_usd": order.total_usd,
        }
        _log(session, "lookup", "get_order_db",
             {"order_id": order_id}, result)
        session.commit()
        return result

@tool("get_shipment_db", args_schema=OrderInput)
def get_shipment_db(order_id: str) -> dict:
    """Retrieve shipment tracking information for an order from database."""
    with SessionLocal() as session:
        # Check order exists
        order = session.get(Order, order_id) 
        if not order:
            raise ValueError(f"Order '{order_id}' not found.")

        # Find shipment for this order
        shipment = session.query(Shipment).filter(
            Shipment.order_id == order_id
        ).first()

        if not shipment:
            raise ValueError(
                f"No shipment record for order '{order_id}' — order may still be processing."
            )
        result = {
            "order_id": shipment.order_id,
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "estimated_delivery": shipment.estimated_delivery,
        } 
        _log(session, "lookup", "get_shipment_db",
             {"order_id": order_id}, result)
        session.commit()
        return result   

@tool("check_inventory_db", args_schema=InventoryInput)
def check_inventory_db(product_id: str):
    """Check inventory level for a product from database."""
    with SessionLocal() as session:
        item = session.get(Inventory, product_id)
        if not item:
            raise ValueError(f"Product '{product_id}' not found.")
        result = {
            "product_id": item.product_id,
            "product_name": item.product_name,
            "stock":        item.stock,
            "warehouse":    item.warehouse,
        } 
        _log(session, "lookup", "check_inventory_db",
             {"product_id": product_id}, result) 
        session.commit()
        return result

@tool
def get_refund_policy_db() -> str:
    """Return the company refund policy text."""
    return (
        "Refunds are accepted within 30 days of purchase. "
        "Items must be unused and in original packaging. "
        "Refunds of USD 500 or above require manager approval. "
        "Digital products are non-refundable once downloaded."
    )


