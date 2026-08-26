# projects/operations_agent/database/seed.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.operations_agent.database.engine import engine, SessionLocal
from projects.operations_agent.database.models import (
    Base, Customer, Order, Shipment, Inventory
)

def create_tables():
    Base.metadata.create_all(engine)
    print("  [seed] Tables created.")

def seed_data():
    session = SessionLocal()
    try:
        # Skip if already seeded
        if session.query(Customer).count() > 0:
            print("  [seed] Data already exists — skipping.")
            return

        # ── Customers ─────────────────────────────────────────────────────
        customers = [
            Customer(id="C001", name="Alice Smith",  email="alice@example.com", tier="premium",  status="active"),
            Customer(id="C002", name="Bob Jones",    email="bob@example.com",   tier="standard", status="active"),
            Customer(id="C003", name="Sara Khan",    email="sara@example.com",  tier="premium",  status="suspended"),
        ]
        session.add_all(customers)

        # ── Orders ────────────────────────────────────────────────────────
        orders = [
            Order(id="O001", customer_id="C001", product_id="P001", quantity=2, status="shipped",    total_usd=149.99),
            Order(id="O002", customer_id="C002", product_id="P002", quantity=1, status="processing", total_usd=49.99),
            Order(id="O003", customer_id="C001", product_id="P003", quantity=1, status="delivered",  total_usd=299.99),
        ]
        session.add_all(orders)

        # ── Shipments ─────────────────────────────────────────────────────
        shipments = [
            Shipment(id="SH001", order_id="O001", carrier="FedEx", tracking_number="FX123456789",
                     status="in_transit",  estimated_delivery="2026-08-25"),
            Shipment(id="SH003", order_id="O003", carrier="UPS",   tracking_number="UP987654321",
                     status="delivered",   estimated_delivery="2026-08-18"),
        ]
        session.add_all(shipments)

        # ── Inventory ─────────────────────────────────────────────────────
        inventory = [
            Inventory(product_id="P001", product_name="Wireless Headphones", stock=42, warehouse="WH-North"),
            Inventory(product_id="P002", product_name="USB-C Hub",           stock=0,  warehouse="WH-South"),
            Inventory(product_id="P003", product_name="Laptop Stand",        stock=15, warehouse="WH-North"),
        ]
        session.add_all(inventory)

        session.commit()
        print("  [seed] Seed data inserted: 3 customers, 3 orders, 2 shipments, 3 inventory items.")

    except Exception as e:
        session.rollback()
        print(f"  [seed] Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_tables()
    seed_data()            
