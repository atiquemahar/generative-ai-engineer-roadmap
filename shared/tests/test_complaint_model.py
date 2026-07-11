import pytest
from pydantic import ValidationError
from shared.models.complaint import Complaint

class TestComplaintValidators:
    """Tests for Pydantic model validators — no API calls needed."""

    def test_valid_complaint_instantiates(self):
        complaint = Complaint(
            intent="shipment_delay",
            priority="medium",
            customer_id="C001",
            order_id="O123",
            requested_action="check delivery action",
            missing_fields=[],
            confidence="high"
        )
        assert complaint.intent == "shipment_delay"
        assert complaint.customer_id == "C001"

    def test_confidence_float_normalized_to_high(self):
        complaint = Complaint(
            intent= "general_inquiry", priority= "low",
            requested_action= "help", missing_fields=[],
            confidence=0.95
        )  

        assert complaint.confidence == "high"

    def test_confidence_float_normalized_to_medium(self):
        complaint = Complaint(
            intent="general_inquiry", priority="low",
            requested_action="help", missing_fields=[],
            confidence=0.60
        )      

        assert complaint.confidence == "medium"

    def test_confidence_float_normalized_to_low(self):
        complaint = Complaint(
            intent="general_inquiry", priority="low",
            requested_action="help", missing_fields=[],
            confidence=0.30
        ) 

        assert complaint.confidence == "low"

    def test_intent_capital_noemalized_to_lowercase(self):
        complaint = Complaint(
            intent="Shipment_delay", priority="low",
            requested_action="help", missing_fields=[],
            confidence="high"
        )  

        assert complaint.intent == "shipment_delay"

    def test__customer_id_must_start_with_c(self):
        with pytest.raises(ValidationError):
            Complaint(
                intent="general_inquiry", priority="low",
                customer_id="X001", #wrong prefix
                requested_action="help",
                missing_fields=[], confidence="high"
            )  

    def test_order_id_must_start_with_o(self):
        with pytest.raises(ValidationError):
            Complaint(
                intent="general_inquiry", priority="low",
                order_id="P123",
                requested_action="help",
                missing_fields=[], confidence="high"
            )   

    def test_customer_id_none_is_valid(self):
        complaint = Complaint(
            intent="general_inquiry", priority="low",
            customer_id=None,
            requested_action="help",
            missing_fields=["customer_id"], confidence="high"
        )

        assert complaint.customer_id is None

    def test_invalid_intent_raises_error(self):
        with pytest.raises(ValidationError):
            Complaint(
                intent="unknown_intent", # not in literal
                priority="low",
                requested_action="help",
                missing_fields=[], confidence="high"
            )

    def test_invalid_priority_raises_error(self):
        with pytest.raises(ValidationError):
            Complaint(
                intent="general_inquiry",
                priority="urgent", # not in literal
                requested_action="help",
                missing_fields=[], confidence="high"
            )                

