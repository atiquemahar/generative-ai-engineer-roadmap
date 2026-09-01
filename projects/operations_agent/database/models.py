# projects/operations_agent/database/models.py
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"

    id:     Mapped[str]     = mapped_column(String, primary_key=True)
    name:   Mapped[str]     = mapped_column(String, nullable=False)
    email:  Mapped[str]     = mapped_column(String, nullable=False)
    tier:   Mapped[str]     = mapped_column(String, default="standard")
    status: Mapped[str]     = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"Customer(id={self.id!r}, name={self.name!r}, tier={self.tier!r})"

class Order(Base):
    __tablename__ = "orders"

    id:             Mapped[str]     = mapped_column(String, primary_key=True) 
    customer_id:    Mapped[str]     = mapped_column(String, ForeignKey("customers.id"), nullable=False)
    product_id:     Mapped[str]     = mapped_column(String, nullable=False)
    quantity:       Mapped[int]     = mapped_column(Integer, nullable=False)
    status:         Mapped[str]     = mapped_column(String, default="processing")
    total_usd:      Mapped[float]   = mapped_column(Float, nullable=False)
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc)) 

    def __repr__(self) -> str:
        return f"Order(id={self.id!r}, customer_id={self.customer_id!r}, status={self.status!r})"

class Shipment(Base):
    __tablename__ = "shipments"

    id:         Mapped[str]     = mapped_column(String, primary_key=True) 
    order_id:   Mapped[str]     = mapped_column(String, ForeignKey("orders.id"), nullable=False) 
    carrier:    Mapped[str]     = mapped_column(String, nullable=False)
    tracking_number: Mapped[str] = mapped_column(String, nullable=False) 
    status:     Mapped[str]     = mapped_column(String, default="processing")
    estimated_delivery: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return f"Shipment(order_id={self.order_id!r}, status={self.status!r})"

class Inventory(Base):
    __tablename__ = "inventory" 

    product_id:     Mapped[str]     = mapped_column(String, primary_key=True)  # P001
    product_name:   Mapped[str]     = mapped_column(String, nullable=False) 
    stock:          Mapped[int]     = mapped_column(Integer, default=0) 
    warehouse:      Mapped[str]     = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"Inventory(product_id={self.product_id!r}, stock={self.stock!r})"

class AuditLog(Base):
    __tablename__ = "audit_logs" 

    id:             Mapped[int]               = mapped_column(primary_key=True)
    action_id:      Mapped[Optional[str]]     = mapped_column(String, unique=True, nullable=True)  # ← idempotency key
    session_id:     Mapped[Optional[str]]     = mapped_column(String) 
    customer_id:    Mapped[Optional[str]]     = mapped_column(String)
    action:         Mapped[Optional[str]]     = mapped_column(String)
    tool_name:      Mapped[Optional[str]]     = mapped_column(String)
    tool_input:     Mapped[Optional[str]]     = mapped_column(JSON) 
    tool_output:    Mapped[Optional[str]]     = mapped_column(JSON)  
    agent_decision: Mapped[Optional[str]]     = mapped_column(String) 
    timestamp:      Mapped[datetime]          = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc)) 

    def __repr__(self) -> str:
        return f"AuditLog(id={self.id!r}, action_id={self.action_id!r}, action={self.action!r})"      


