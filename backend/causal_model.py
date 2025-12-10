import sqlite3
import networkx as nx

DB_PATH = "database/medical_knowledge.db"

class CausalModel:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def build_transition_graph(self):
        """
        Builds a directed graph from the disease_transitions table.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT from_disease, to_disease, transition_prob FROM disease_transitions")
        transitions = cursor.fetchall()
        conn.close()
        
        G = nx.DiGraph()
        for u, v, prob in transitions:
            G.add_edge(u, v, weight=prob)
            
        return G

    def get_next_likely_diseases(self, current_disease_code, top_k=3):
        """
        Returns the top_k most likely next diseases based on transition probabilities.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT to_disease, transition_prob
            FROM disease_transitions
            WHERE from_disease = ?
            ORDER BY transition_prob DESC
            LIMIT ?
        """, (current_disease_code, top_k))
        
        results = cursor.fetchall()
        conn.close()
        
        predictions = []
        for row in results:
            predictions.append({
                "disease_code": row[0],
                "probability": row[1]
            })
            
        return predictions

    def get_causal_path(self, start_disease, end_disease):
        """
        Finds the most likely path between two diseases.
        """
        G = self.build_transition_graph()
        try:
            path = nx.shortest_path(G, source=start_disease, target=end_disease, weight='weight')
            return path
        except nx.NetworkXNoPath:
            return []
