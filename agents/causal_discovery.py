"""
CausalDiscoveryAgent - Generates and refines disease progression DAGs

This agent builds directed acyclic graphs (DAGs) representing causal relationships
between diseases using transition matrices and iteratively refines them using
document signals and clinician feedback.
"""

import sqlite3
import json
import numpy as np
from typing import List, Dict, Tuple


class CausalDiscoveryAgent:
    """
    Agent for discovering and refining causal relationships between diseases.
    
    Generates DAGs from transition probabilities and refines them using
    document evidence and fit scoring.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the Causal Discovery Agent.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def build_candidate_set(
        self,
        patient_id: int,
        visit_id: int,
        epsilon: float = 0.01
    ) -> List[str]:
        """
        Build candidate disease set from transition matrix.
        
        Args:
            patient_id: Patient ID
            visit_id: Visit ID (typically the last visit)
            epsilon: Minimum probability threshold
            
        Returns:
            List of candidate disease codes sorted by probability (descending)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get diagnoses from the specified visit
        cursor.execute("""
            SELECT DISTINCT disease_code
            FROM diagnoses
            WHERE visit_id = ?
        """, (visit_id,))
        
        current_diseases = [row[0] for row in cursor.fetchall()]
        
        if not current_diseases:
            conn.close()
            return []
        
        # Query transition matrix for all current diseases
        candidates = {}
        for disease in current_diseases:
            cursor.execute("""
                SELECT to_disease, transition_prob
                FROM transition_matrix
                WHERE from_disease = ? AND transition_prob > ?
                ORDER BY transition_prob DESC
            """, (disease, epsilon))
            
            for row in cursor.fetchall():
                to_disease, prob = row
                # Keep maximum probability if disease appears multiple times
                if to_disease not in candidates or prob > candidates[to_disease]:
                    candidates[to_disease] = prob
        
        conn.close()
        
        # Sort by probability descending
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [disease for disease, prob in sorted_candidates]
    
    def generate_initial_dag(self, entities: List[str]) -> Dict:
        """
        Generate initial DAG from transition matrix.
        
        Args:
            entities: List of disease codes to include in DAG
            
        Returns:
            DAG dict with nodes and edges
        """
        if not entities:
            return {"nodes": [], "edges": []}
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create nodes
        nodes = [{"id": disease} for disease in entities]
        
        # Query transition matrix for edges between entities
        edges = []
        for from_disease in entities:
            for to_disease in entities:
                if from_disease == to_disease:
                    continue
                
                cursor.execute("""
                    SELECT transition_prob
                    FROM transition_matrix
                    WHERE from_disease = ? AND to_disease = ?
                """, (from_disease, to_disease))
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    edges.append({
                        "from": from_disease,
                        "to": to_disease,
                        "weight": float(result[0])
                    })
        
        conn.close()
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def fit_graph_with_data(self, dag: Dict) -> Dict:
        """
        Compute fit score for DAG using diagnosis matrix.
        
        Uses approximate log-likelihood assuming Bernoulli parents.
        
        Args:
            dag: DAG dict with nodes and edges
            
        Returns:
            DAG augmented with fit_score per edge and global_fit
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        edges = dag.get("edges", [])
        total_fit = 0.0
        
        for edge in edges:
            from_disease = edge["from"]
            to_disease = edge["to"]
            
            # Query diagnosis matrix for co-occurrence
            cursor.execute("""
                SELECT co_occurrence_count, total_patients
                FROM diagnosis_matrix
                WHERE disease_a = ? AND disease_b = ?
            """, (from_disease, to_disease))
            
            result = cursor.fetchone()
            
            if result:
                co_occurrence, total = result
                # Compute log-likelihood (Bernoulli approximation)
                # P(to|from) = co_occurrence / total
                if total > 0:
                    prob = co_occurrence / total
                    # Avoid log(0)
                    if prob > 0:
                        fit_score = np.log(prob)
                    else:
                        fit_score = -10.0  # Penalty for zero probability
                else:
                    fit_score = -10.0
            else:
                # No data available
                fit_score = -5.0
            
            edge["fit_score"] = float(fit_score)
            total_fit += fit_score
        
        conn.close()
        
        dag["global_fit"] = float(total_fit)
        return dag
    
    def iterative_refine(
        self,
        dag: Dict,
        summaries: List[Dict],
        max_iter: int = 3
    ) -> Dict:
        """
        Iteratively refine DAG using document summaries.
        
        Searches for causal phrases in summaries and boosts corresponding edge weights.
        
        Args:
            dag: Initial DAG
            summaries: List of document summaries from KnowledgeSynthesisAgent
            max_iter: Maximum refinement iterations
            
        Returns:
            Refined DAG with modification history
        """
        # Causal phrases to search for
        causal_phrases = [
            "cause", "causes", "caused by",
            "risk factor", "risk factors",
            "leads to", "lead to",
            "associated with", "association with",
            "progression to", "progresses to",
            "results in", "result in"
        ]
        
        modification_history = []
        
        for iteration in range(max_iter):
            modified = False
            
            for edge in dag.get("edges", []):
                from_disease = edge["from"]
                to_disease = edge["to"]
                
                # Check if any summary mentions this causal relationship
                for summary in summaries:
                    content = summary.get("content", "").lower()
                    disease_code = summary.get("disease_code", "").lower()
                    
                    # Check if summary is about one of the diseases in the edge
                    if disease_code not in [from_disease.lower(), to_disease.lower()]:
                        continue
                    
                    # Check for causal phrases
                    for phrase in causal_phrases:
                        if phrase in content:
                            # Boost edge weight by 20%
                            old_weight = edge["weight"]
                            edge["weight"] = min(1.0, old_weight * 1.2)
                            
                            modification_history.append({
                                "iteration": iteration,
                                "edge": f"{from_disease} -> {to_disease}",
                                "reason": f"Found causal phrase '{phrase}' in {disease_code} document",
                                "old_weight": old_weight,
                                "new_weight": edge["weight"]
                            })
                            
                            modified = True
                            break
            
            # Recompute fit scores after modification
            if modified:
                dag = self.fit_graph_with_data(dag)
            else:
                # No modifications made, stop early
                break
        
        dag["modification_history"] = modification_history
        return dag
    
    def apply_clinician_edit(
        self,
        dag: Dict,
        action: str,
        from_disease: str,
        to_disease: str,
        reason: str
    ) -> Dict:
        """
        Apply clinician feedback to DAG.
        
        Args:
            dag: Current DAG
            action: "add_edge", "remove_edge", or "reverse_edge"
            from_disease: Source disease code
            to_disease: Target disease code
            reason: Clinician's reason for edit
            
        Returns:
            Modified DAG
        """
        edges = dag.get("edges", [])
        nodes = dag.get("nodes", [])
        
        if action == "add_edge":
            # Add edge with high weight (clinician override)
            edges.append({
                "from": from_disease,
                "to": to_disease,
                "weight": 0.8,
                "clinician_added": True,
                "reason": reason
            })
            
            # Ensure nodes exist
            node_ids = [n["id"] for n in nodes]
            if from_disease not in node_ids:
                nodes.append({"id": from_disease})
            if to_disease not in node_ids:
                nodes.append({"id": to_disease})
        
        elif action == "remove_edge":
            # Remove edge
            edges = [
                e for e in edges
                if not (e["from"] == from_disease and e["to"] == to_disease)
            ]
        
        elif action == "reverse_edge":
            # Find and reverse edge
            for edge in edges:
                if edge["from"] == from_disease and edge["to"] == to_disease:
                    edge["from"] = to_disease
                    edge["to"] = from_disease
                    edge["clinician_reversed"] = True
                    edge["reason"] = reason
                    break
        
        dag["edges"] = edges
        dag["nodes"] = nodes
        
        # Recompute fit scores
        dag = self.fit_graph_with_data(dag)
        
        return dag
