from pydantic import BaseModel, field_validator
from typing import Literal, Optional 

class Complaint(BaseModel):
    intent: Literal[
        "shipment_delay",
        "refund_request",
        "product_defect",
        "account_issue",
        "general_inquiry"
    ]
    priority: Literal["low", "medium", "high"]
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    requested_action: str
    missing_fields: list[str]
    confidence: Literal["low", "medium", "high"]

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v):
        if v is not None and not v.startswith("C"):
            raise ValueError("customer_id must start with C")
        return v
    
    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v):
        if v is not None and not v.startswith("O"):
            raise ValueError("order_id must start with O")
        return v
    
    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        # Model somtimes rturns 0.95 instead of "high" - convert gracefully
        if isinstance(v, float):
            if v >= 0.75:
                return "high"
            elif v >= 0.45:
                return "medium"
            else:
                return "low"
        return v    

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

        
