import sqlite3
import networkx as nx

DB_PATH = "database/medical_knowledge.db"

class CausalDiscoveryAgent:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def discover_causal_graph(self, current_disease_code, top_k=3):
        """
        Generates a DAG representing the causal relationships from the current disease.
        Returns a JSON-serializable structure (nodes and links).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get direct transitions
        cursor.execute("""
            SELECT to_disease, transition_prob
            FROM disease_transitions
            WHERE from_disease = ?
            ORDER BY transition_prob DESC
            LIMIT ?
        """, (current_disease_code, top_k))
        
        results = cursor.fetchall()
        conn.close()
        
        nodes = [{"id": current_disease_code, "label": f"Current: {current_disease_code}", "type": "current"}]
        links = []
        
        predictions = []
        
        for row in results:
            to_disease = row[0]
            prob = row[1]
            
            nodes.append({"id": to_disease, "label": f"Risk: {to_disease}", "type": "predicted"})
            links.append({"source": current_disease_code, "target": to_disease, "weight": prob})
            
            predictions.append({
                "disease_code": to_disease,
                "probability": prob
            })
            
        dag_json = {
            "nodes": nodes,
            "links": links
        }
            
        return {
            "dag": dag_json,
            "predictions": predictions
        }
