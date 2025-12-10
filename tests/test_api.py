"""
API Integration Tests

Tests for all /agents/* endpoints using FastAPI TestClient.
"""

import pytest
import sqlite3
import json
import os
import sys
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app import app

TEST_DB = "database/medical_knowledge.db"


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Setup test database before running tests."""
    # Run seed_small.py to create test data
    import subprocess
    
    # Ensure database directory exists
    os.makedirs("database", exist_ok=True)
    
    # Run seeding script
    result = subprocess.run(
        [sys.executable, "scripts/seed_small.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        pytest.skip(f"Failed to seed database: {result.stderr}")
    
    yield
    
    # Cleanup is optional - can keep DB for inspection


class TestBasicEndpoints:
    """Test basic patient endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
    
    def test_get_patients(self, client):
        """Test getting all patients."""
        response = client.get("/patients")
        assert response.status_code == 200
        patients = response.json()
        assert isinstance(patients, list)
        assert len(patients) > 0
        
        patient = patients[0]
        assert "patient_id" in patient
        assert "name" in patient
        assert "dob" in patient
        assert "gender" in patient
    
    def test_get_patient_history(self, client):
        """Test getting patient history."""
        response = client.get("/patients/1/history")
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        assert len(history) > 0
        
        diagnosis = history[0]
        assert "visit_date" in diagnosis
        assert "disease_code" in diagnosis
        assert "disease_name" in diagnosis
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "patient_count" in data


class TestAgentsPredictEndpoint:
    """Test /agents/predict endpoint."""
    
    def test_predict_success(self, client):
        """Test successful prediction."""
        response = client.post(
            "/agents/predict",
            json={"patient_id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "predictions" in data
        assert "explanation" in data
        assert "evidence" in data
        assert "dag" in data
        assert "prediction_id" in data
        
        # Verify predictions structure
        if data["predictions"]:
            pred = data["predictions"][0]
            assert "code" in pred
            assert "score" in pred
            assert 0 <= pred["score"] <= 1
        
        # Verify DAG structure
        dag = data["dag"]
        assert "nodes" in dag
        assert "edges" in dag
    
    def test_predict_with_clinician_comment(self, client):
        """Test prediction with clinician comment."""
        response = client.post(
            "/agents/predict",
            json={
                "patient_id": 1,
                "clinician_comment": "Prioritize kidney outcomes"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
    
    def test_predict_invalid_patient(self, client):
        """Test prediction for non-existent patient."""
        response = client.post(
            "/agents/predict",
            json={"patient_id": 99999}
        )
        
        assert response.status_code == 404
    
    def test_prediction_stored_in_db(self, client):
        """Test that prediction is stored in database."""
        # Make prediction
        response = client.post(
            "/agents/predict",
            json={"patient_id": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        prediction_id = data["prediction_id"]
        
        # Verify in database
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM predictions WHERE prediction_id = ?",
            (prediction_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None


class TestAgentsRefineEndpoint:
    """Test /agents/refine endpoint."""
    
    def test_refine_add_edge(self, client):
        """Test adding edge to DAG."""
        # First make a prediction
        client.post("/agents/predict", json={"patient_id": 1})
        
        # Then refine
        response = client.post(
            "/agents/refine",
            json={
                "patient_id": 1,
                "feedback": {
                    "action": "add_edge",
                    "from": "I10",
                    "to": "I50.9",
                    "reason": "Clinician: HTN directly causes HF in this case"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dag" in data
        assert "predictions" in data
        
        # Check that edge was added
        dag = data["dag"]
        edges = dag.get("edges", [])
        edge_found = any(
            e["from"] == "I10" and e["to"] == "I50.9"
            for e in edges
        )
        assert edge_found
    
    def test_refine_invalid_feedback(self, client):
        """Test refine with invalid feedback."""
        response = client.post(
            "/agents/refine",
            json={
                "patient_id": 1,
                "feedback": {
                    "action": "add_edge"
                    # Missing from and to
                }
            }
        )
        
        assert response.status_code == 400


class TestAgentsDAGEndpoint:
    """Test /agents/dag/{patient_id} endpoint."""
    
    def test_get_dag(self, client):
        """Test getting DAG for patient."""
        # First make a prediction
        client.post("/agents/predict", json={"patient_id": 1})
        
        # Get DAG
        response = client.get("/agents/dag/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "patient_id" in data
        assert "dag" in data
        assert data["patient_id"] == 1
        
        dag = data["dag"]
        assert "nodes" in dag
        assert "edges" in dag
    
    def test_get_dag_no_prediction(self, client):
        """Test getting DAG for patient with no predictions."""
        response = client.get("/agents/dag/999")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty DAG
        dag = data["dag"]
        assert dag["nodes"] == []
        assert dag["edges"] == []


class TestAgentsUploadDocEndpoint:
    """Test /agents/upload_doc endpoint."""
    
    def test_upload_text_file(self, client):
        """Test uploading text file."""
        content = b"This is a test medical document about hypertension and kidney disease."
        
        response = client.post(
            "/agents/upload_doc",
            files={"file": ("test.txt", BytesIO(content), "text/plain")},
            data={"disease_code": "I10"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "doc_ids" in data
        assert "preview_snippets" in data
        assert len(data["doc_ids"]) > 0
    
    def test_upload_without_disease_code(self, client):
        """Test uploading without disease code."""
        content = b"Test document content."
        
        response = client.post(
            "/agents/upload_doc",
            files={"file": ("test.txt", BytesIO(content), "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["disease_code"] is None


class TestChatEndpoint:
    """Test /agents/chat endpoint."""
    
    def test_chat_success(self, client):
        """Test successful chat interaction."""
        response = client.post(
            "/agents/chat",
            json={
                "patient_id": 1,
                "message": "What should I watch for next?"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "reply" in data
        assert "conversation_id" in data
        assert "patient_id" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0
    
    def test_chat_conversation_stored(self, client):
        """Test that chat is stored in database."""
        response = client.post(
            "/agents/chat",
            json={
                "patient_id": 1,
                "message": "Test message"
            }
        )
        
        assert response.status_code == 200
        
        # Verify in database
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE patient_id = 1"
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        # Should have at least user message and assistant reply
        assert count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
