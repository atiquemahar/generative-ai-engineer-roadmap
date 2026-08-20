# projects/operations-agent/tools/read_tools.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import TypedDict


# ── Return types ───────────────────────────────────────────────────────────

class CustomerRecord(TypedDict):
    name: str
    email: str
    tier: str
    status: str

class OrderRecord(TypedDict):
    customer_id: str
    product_id: str
    quantity: int
    status: str
    total_usd: float

class ShipmentRecord(TypedDict):
    order_id: str
    carrier: str
    tracking_number: str
    status: str
    estimated_delivery: str

class InventoryRecord(TypedDict):
    product_id: str
    product_name: str
    stock: int
    warehouse: str

# ── Input schemas ──────────────────────────────────────────────────────────

class CustomerInput(BaseModel):
    customer_id: str = Field(description="Customer ID starting with C, e.g. C001")

class OrderInput(BaseModel):
    order_id: str = Field(description="Order ID starting with O, e.g. O001")

class InventoryInput(BaseModel):
    product_id: str = Field(description="Product ID starting with P, e.g. P001")

# ── Mock databases ─────────────────────────────────────────────────────────

_CUSTOMERS: dict[str, CustomerRecord] = {
    "C001": {"name": "Alice Smith",  "email": "alice@example.com", "tier": "premium",  "status": "active"},
    "C002": {"name": "Bob Jones",    "email": "bob@example.com",   "tier": "standard", "status": "active"},
    "C003": {"name": "Sara Khan",    "email": "sara@example.com",  "tier": "premium",  "status": "suspended"},
}

_ORDERS: dict[str, OrderRecord] = {
    "O001": {"customer_id": "C001", "product_id": "P001", "quantity": 2, "status": "shipped",    "total_usd": 149.99},
    "O002": {"customer_id": "C002", "product_id": "P002", "quantity": 1, "status": "processing", "total_usd": 49.99},
    "O003": {"customer_id": "C001", "product_id": "P003", "quantity": 1, "status": "delivered",  "total_usd": 299.99},
}

_SHIPMENTS: dict[str, ShipmentRecord] = {
    "O001": {"order_id": "O001", "carrier": "FedEx", "tracking_number": "FX123456789",
             "status": "in_transit",  "estimated_delivery": "2026-08-25"},
    "O003": {"order_id": "O003", "carrier": "UPS",   "tracking_number": "UP987654321",
             "status": "delivered",   "estimated_delivery": "2026-08-18"},
}

_INVENTORY: dict[str, InventoryRecord] = {
    "P001": {"product_id": "P001", "product_name": "Wireless Headphones", "stock": 42,  "warehouse": "WH-North"},
    "P002": {"product_id": "P002", "product_name": "USB-C Hub",           "stock": 0,   "warehouse": "WH-South"},
    "P003": {"product_id": "P003", "product_name": "Laptop Stand",        "stock": 15,  "warehouse": "WH-North"},
}

# ── Tools ──────────────────────────────────────────────────────────────────


@tool("get_customer", args_schema=CustomerInput)
def get_customer(customer_id: str) -> CustomerRecord:
    """Retrieve customer information by ID. Returns name, email, tier, and account status."""
    if customer_id not in _CUSTOMERS:
        raise ValueError(f"Customer '{customer_id}' not found. Valid IDs: {list(_CUSTOMERS.keys())}")
    return _CUSTOMERS[customer_id]

@tool("get_order", args_schema=OrderInput)
def get_order(order_id: str) -> OrderRecord:
    """Retrieve order details by order ID. Returns customer ID, product, quantity, status, and total."""
    if order_id not in _ORDERS:
         raise ValueError(f"Order '{order_id}' not found. Valid IDs: {list(_ORDERS.keys())}")
    return _ORDERS[order_id]

@tool("get_shipment", args_schema=OrderInput)
def get_shipment(order_id: str) -> ShipmentRecord:
    """Retrieve shipment tracking information for an order. Returns carrier, tracking number, status, and estimated delivery."""
    if order_id not in _ORDERS:
        raise ValueError(f"Order '{order_id}' not found.")
    if order_id not in _SHIPMENTS:
        raise ValueError(f"No shipment record for order '{order_id}' — order may still be processing.")
    return _SHIPMENTS[order_id]

@tool("check_inventory", args_schema=InventoryInput)
def check_inventory(product_id: str) -> InventoryRecord:
    """Check current inventory level for a product. Returns product name, stock count, and warehouse location."""
    if product_id not in _INVENTORY:
        raise ValueError(f"Product '{product_id}' not found. Valid IDs: {list(_INVENTORY.keys())}")
    return _INVENTORY[product_id]

@tool
def get_refund_policy() -> str:
    """Return the company refund policy text. No input required."""
    return (
        "Refunds are accepted within 30 days of purchase. "
        "Items must be unused and in original packaging. "
        "Refunds of USD 500 or above require manager approval. "
        "Digital products are non-refundable once downloaded."
    )