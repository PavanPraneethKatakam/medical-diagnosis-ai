"""
Unit Tests for Agent Classes

Tests for KnowledgeSynthesisAgent, CausalDiscoveryAgent, and DecisionMakingAgent.
"""

import pytest
import sqlite3
import json
import os
import sys
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import KnowledgeSynthesisAgent, CausalDiscoveryAgent, DecisionMakingAgent

TEST_DB = "test_medical.db"


@pytest.fixture(scope="function")
def test_db():
    """Create test database with minimal data."""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY,
            name TEXT,
            dob TEXT,
            gender TEXT
        );
        
        CREATE TABLE IF NOT EXISTS visits (
            visit_id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            visit_date TEXT
        );
        
        CREATE TABLE IF NOT EXISTS diagnoses (
            diagnosis_id INTEGER PRIMARY KEY,
            visit_id INTEGER,
            disease_code TEXT,
            disease_name TEXT
        );
        
        CREATE TABLE IF NOT EXISTS transition_matrix (
            from_disease TEXT,
            to_disease TEXT,
            transition_prob FLOAT,
            support_count INTEGER DEFAULT 0,
            PRIMARY KEY (from_disease, to_disease)
        );
        
        CREATE TABLE IF NOT EXISTS diagnosis_matrix (
            disease_a TEXT,
            disease_b TEXT,
            co_occurrence_count INTEGER,
            total_patients INTEGER,
            PRIMARY KEY (disease_a, disease_b)
        );
        
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            doc_id INTEGER PRIMARY KEY,
            disease_code TEXT,
            section TEXT,
            content TEXT
        );
        
        CREATE TABLE IF NOT EXISTS document_embeddings (
            doc_id INTEGER PRIMARY KEY,
            embedding TEXT
        );
        
        CREATE TABLE IF NOT EXISTS knowledge_summary_cache (
            cache_id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            visit_id INTEGER,
            doc_id INTEGER,
            summary TEXT,
            similarity FLOAT,
            created_at TEXT
        );
    """)
    
    # Insert test data
    cursor.execute("INSERT INTO patients VALUES (1, 'Test Patient', '1960-01-01', 'M')")
    cursor.execute("INSERT INTO visits VALUES (1, 1, '2023-01-01')")
    cursor.execute("INSERT INTO visits VALUES (2, 1, '2023-06-01')")
    cursor.execute("INSERT INTO diagnoses VALUES (1, 1, 'I10', 'Hypertension')")
    cursor.execute("INSERT INTO diagnoses VALUES (2, 2, 'N18.9', 'CKD')")
    
    # Transition matrix
    cursor.execute("INSERT INTO transition_matrix VALUES ('I10', 'N18.9', 0.40, 100)")
    cursor.execute("INSERT INTO transition_matrix VALUES ('I10', 'I25.10', 0.30, 75)")
    cursor.execute("INSERT INTO transition_matrix VALUES ('N18.9', 'I50.9', 0.60, 120)")
    
    # Diagnosis matrix
    cursor.execute("INSERT INTO diagnosis_matrix VALUES ('I10', 'N18.9', 50, 200)")
    cursor.execute("INSERT INTO diagnosis_matrix VALUES ('I10', 'I25.10', 40, 200)")
    
    # Knowledge documents with embeddings
    docs = [
        (1, 'I10', 'Causes', 'Hypertension is caused by high salt intake and obesity. It is a risk factor for chronic kidney disease.'),
        (2, 'N18.9', 'Progression', 'Chronic kidney disease leads to heart failure in many patients due to fluid overload.'),
        (3, 'I25.10', 'Symptoms', 'Coronary artery disease causes chest pain and shortness of breath.'),
    ]
    
    for doc_id, code, section, content in docs:
        cursor.execute("INSERT INTO knowledge_documents VALUES (?, ?, ?, ?)", (doc_id, code, section, content))
        # Create simple embedding (5-dimensional for testing)
        embedding = [0.1 * doc_id, 0.2 * doc_id, -0.1 * doc_id, 0.3 * doc_id, -0.2 * doc_id]
        cursor.execute("INSERT INTO document_embeddings VALUES (?, ?)", (doc_id, json.dumps(embedding)))
    
    conn.commit()
    conn.close()
    
    yield TEST_DB
    
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestKnowledgeSynthesisAgent:
    """Tests for KnowledgeSynthesisAgent."""
    
    def test_generate_query(self, test_db):
        """Test query generation from diagnosis history and candidates."""
        agent = KnowledgeSynthesisAgent(test_db)
        
        diagnosis_history = ["I10", "N18.3", "N18.4"]
        candidates = ["I50.9", "D63.1"]
        
        query = agent.generate_query(diagnosis_history, candidates)
        
        assert isinstance(query, str)
        assert len(query) > 0
        assert "I10" in query or "N18.3" in query or "N18.4" in query
    
    def test_retrieve_and_summarize(self, test_db):
        """Test document retrieval and summarization."""
        agent = KnowledgeSynthesisAgent(test_db)
        
        query = "hypertension kidney disease"
        results = agent.retrieve_and_summarize(query, top_k=3)
        
        assert isinstance(results, list)
        assert len(results) <= 3
        
        if results:
            result = results[0]
            assert "doc_id" in result
            assert "disease_code" in result
            assert "summary" in result
            assert "similarity" in result
            assert 0 <= result["similarity"] <= 1
            assert len(result["summary"]) > 0
    
    def test_store_summary_cache(self, test_db):
        """Test caching of summaries."""
        agent = KnowledgeSynthesisAgent(test_db)
        
        summaries = [
            {"doc_id": 1, "summary": "Test summary", "similarity": 0.85}
        ]
        
        agent.store_summary_cache(1, 1, summaries)
        
        # Verify cache entry
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge_summary_cache WHERE patient_id=1")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1


class TestCausalDiscoveryAgent:
    """Tests for CausalDiscoveryAgent."""
    
    def test_build_candidate_set(self, test_db):
        """Test candidate disease set building."""
        agent = CausalDiscoveryAgent(test_db)
        
        candidates = agent.build_candidate_set(1, 1, epsilon=0.01)
        
        assert isinstance(candidates, list)
        # Should find N18.9 and I25.10 from I10
        assert len(candidates) >= 1
        if candidates:
            assert candidates[0] in ["N18.9", "I25.10"]
    
    def test_generate_initial_dag(self, test_db):
        """Test DAG generation from entities."""
        agent = CausalDiscoveryAgent(test_db)
        
        entities = ["I10", "N18.9", "I50.9"]
        dag = agent.generate_initial_dag(entities)
        
        assert "nodes" in dag
        assert "edges" in dag
        assert len(dag["nodes"]) == 3
        
        # Should have edges based on transition matrix
        assert len(dag["edges"]) >= 1
        
        if dag["edges"]:
            edge = dag["edges"][0]
            assert "from" in edge
            assert "to" in edge
            assert "weight" in edge
            assert edge["weight"] > 0
    
    def test_fit_graph_with_data(self, test_db):
        """Test DAG fit scoring."""
        agent = CausalDiscoveryAgent(test_db)
        
        dag = {
            "nodes": [{"id": "I10"}, {"id": "N18.9"}],
            "edges": [{"from": "I10", "to": "N18.9", "weight": 0.40}]
        }
        
        fitted_dag = agent.fit_graph_with_data(dag)
        
        assert "global_fit" in fitted_dag
        assert "fit_score" in fitted_dag["edges"][0]
    
    def test_iterative_refine(self, test_db):
        """Test DAG refinement with causal phrases."""
        agent = CausalDiscoveryAgent(test_db)
        
        dag = {
            "nodes": [{"id": "I10"}, {"id": "N18.9"}],
            "edges": [{"from": "I10", "to": "N18.9", "weight": 0.40}]
        }
        
        summaries = [
            {
                "disease_code": "I10",
                "content": "Hypertension is a risk factor for chronic kidney disease.",
                "similarity": 0.9
            }
        ]
        
        refined_dag = agent.iterative_refine(dag, summaries, max_iter=2)
        
        assert "modification_history" in refined_dag
        # Weight should increase due to "risk factor" phrase
        if refined_dag["modification_history"]:
            assert refined_dag["edges"][0]["weight"] > 0.40


class TestDecisionMakingAgent:
    """Tests for DecisionMakingAgent."""
    
    def test_rank_and_explain_structure(self, test_db):
        """Test that rank_and_explain returns correct structure."""
        agent = DecisionMakingAgent()
        
        patient_summary = "Patient with hypertension"
        candidates = [("N18.9", 0.40), ("I25.10", 0.30)]
        dag = {"nodes": [], "edges": []}
        summaries = []
        
        result = agent.rank_and_explain(
            patient_summary, candidates, dag, summaries, ""
        )
        
        assert isinstance(result, dict)
        assert "predictions" in result
        assert "explanation" in result
        assert "evidence" in result
        assert "dag" in result
        
        if result["predictions"]:
            pred = result["predictions"][0]
            assert "code" in pred
            assert "score" in pred
            assert "rank" in pred
            assert 0 <= pred["score"] <= 1
    
    def test_deterministic_fallback(self, test_db):
        """Test deterministic fallback ranking."""
        agent = DecisionMakingAgent()
        
        patient_summary = "Patient with hypertension"
        candidates = [("N18.9", 0.40), ("I25.10", 0.30), ("I50.9", 0.25)]
        dag = {"nodes": [], "edges": []}
        summaries = [
            {"disease_code": "N18.9", "similarity": 0.85, "doc_id": 1, "summary": "CKD info"}
        ]
        clinician_comment = "Focus on kidney outcomes"
        
        result = agent._deterministic_fallback(
            patient_summary, candidates, dag, summaries, clinician_comment
        )
        
        assert result["fallback"] is True
        assert len(result["predictions"]) == 3
        
        # Check scoring formula
        pred = result["predictions"][0]
        assert "transition_score" in pred
        assert "doc_similarity" in pred
        assert "clinician_boost" in pred
        
        # Final score should be weighted combination
        expected_score = (
            0.6 * pred["transition_score"] +
            0.3 * pred["doc_similarity"] +
            0.1 * pred["clinician_boost"]
        )
        assert abs(pred["score"] - expected_score) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
