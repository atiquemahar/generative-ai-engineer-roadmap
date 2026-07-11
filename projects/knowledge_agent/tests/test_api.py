import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from projects.knowledge_agent.api.main import app
from projects.knowledge_agent.api.dependencies import get_project_client
from shared.models.complaint import Complaint

# Fast tets: ----- No Azure API calls

class TestHealthEndpoint:
    def setup_method(self):
        self.client = TestClient(app)

    def test_health_returns_200(self):
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        response = self.client.get("/health") 
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self):
        response = self.client.get("/health") 
        data = response.json() 
        assert "version" in data

class TestExtractValidation:
    """Validation tests — 422 responses, no Azure call made."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_missing_body_returns_422(self):
        response = self.client.post("/extract/", json={})  
        assert response.status_code == 422 

    def test_missing_body_includes_trace_id(self):
        response =self.client.post("/extract/", json={})
        data = response.json()
        assert "trace_id" in data

    def test_missing_body_includes_field_detail(self):
        response =self.client.post("/extract/", json={})
        data = response.json()
        assert data["error"] == "validation_failed"
        assert any(
            "text_to_analyze" in str(detail) 
            for detail in data["details"]
        )

    def test_wrong_field_names_returns_422(self):
        # Sending "message" instead of "text_to_analyze"
        response = self.client.post("/extract/", json={"message": "hello"})
        assert response.status_code == 422

class TestForceError:
    """Test general exception handler."""

    def setup_method(self):
        self.client = TestClient(app, raise_server_exceptions=False) 

    def test_force_error_returns_500(self):
        response = self.client.get("/force-error") 
        assert response.status_code == 500

    def test_force_error_returns_trace_id(self):
        response = self.client.get("/force-error")
        data = response.json()
        assert "trace_id" in data
        assert data["error"] == "internal_error"                  


# ── Slow tests: real Azure API calls ───────────────────────────────────

@pytest.mark.integration
class TestExtractIntegration:
    """Real API calls to Azure — run manually, not in CI."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_extract_valid_complaint_returns_200(self):
        response = self.client.post(
            "/extract/",
            json={"text_to_analyze": "My order O123 is delayed. Customer C456."}
        )  
        assert response.status_code == 200

    def test_extract_returns_intent_filed(self):
        response = self.client.post(
            "/extract/",
            json={"text_to_analyze": "My order O123 is delayed. Customer C456."}
        )
        data = response.json()
        assert "intent" in data
        assert data["intent"] in [
            "shipment_delay", "refund_request",
            "product_defect", "account_issue", "general_inquiry"
        ]   

    def test_extract_detects_order_id(self):
        response = self.client.post(
            "/extract/",
            json={"text_to_analyze": "Where is order O789? Customer C111."}
        )
        data = response.json()  
        assert data["order_id"] == "O789"

@pytest.mark.integration
class TestChatIntegration:
    def setup_method(self):
        self.client = TestClient(app)  

    def test_chat_returns_200(self):
        response = self.client.post(
            "/chat/",
            json={"message": "What is Azure AI Foundry in one sentence?"}
        )
        assert response.status_code == 200

    def test_chat_returns_reply_field(self):
        response = self.client.post(
            "/chat/",
            json={"message": "Say hello."}
        )
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0               
