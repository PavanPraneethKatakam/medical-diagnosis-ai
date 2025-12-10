"""
KnowledgeSynthesisAgent - Retrieves and summarizes medical knowledge using embeddings

This agent uses sentence-transformers to perform semantic search over medical documents
and generates extractive summaries of the most relevant knowledge.
"""

import sqlite3
import json
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from .model_pool import get_model_pool


class KnowledgeSynthesisAgent:
    """
    Agent for retrieving and synthesizing medical knowledge using semantic search.
    
    Uses sentence-transformers for embedding generation and cosine similarity
    for document retrieval.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = "database/medical_knowledge.db"):
        """
        Initialize the Knowledge Synthesis Agent.
        
        Args:
            model_name: Sentence-transformer model name
            db_path: Path to SQLite database
        """
        self.model_name = model_name
        self.db_path = db_path
        # Use model pool singleton
        model_pool = get_model_pool()
        self.model = model_pool.load_embedding_model(model_name)
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def generate_query(self, diagnosis_history: List[str], candidates: List[str]) -> str:
        """
        Generate a concise query string from diagnosis history and candidates.
        
        Args:
            diagnosis_history: List of disease codes from patient history
            candidates: List of candidate disease codes
            
        Returns:
            Query string for semantic search
        """
        # Deterministic query generation
        history_str = " ".join(diagnosis_history[-3:])  # Last 3 diagnoses
        candidates_str = " ".join(candidates[:5])  # Top 5 candidates
        
        query = f"patient history {history_str} risk factors progression {candidates_str}"
        return query
    
    def retrieve_and_summarize(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Retrieve top-k most relevant documents and generate summaries.
        
        Args:
            query: Search query string
            top_k: Number of documents to retrieve
            
        Returns:
            List of dicts with doc_id, disease_code, section, summary, embedding, similarity
        """
        # Compute query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Load all document embeddings from database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT de.doc_id, kd.disease_code, kd.section, kd.content, de.embedding
            FROM document_embeddings de
            JOIN knowledge_documents kd ON de.doc_id = kd.doc_id
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return []
        
        # Compute cosine similarities
        similarities = []
        for row in results:
            doc_id, disease_code, section, content, embedding_json = row
            
            # Parse embedding from JSON
            doc_embedding = np.array(json.loads(embedding_json))
            
            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            
            # Generate extractive summary (first 200 chars, trimmed to full sentence)
            summary = self._generate_summary(content)
            
            similarities.append({
                "doc_id": doc_id,
                "disease_code": disease_code,
                "section": section,
                "summary": summary,
                "embedding": doc_embedding.tolist(),
                "similarity": float(similarity),
                "content": content  # Keep full content for reference
            })
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score [0, 1]
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return max(0.0, min(1.0, dot_product / (norm1 * norm2)))
    
    def _generate_summary(self, content: str, max_chars: int = 200) -> str:
        """
        Generate extractive summary from content.
        
        Args:
            content: Full document content
            max_chars: Maximum characters in summary
            
        Returns:
            Summary string (first max_chars, trimmed to full sentence)
        """
        if len(content) <= max_chars:
            return content
        
        # Take first max_chars
        truncated = content[:max_chars]
        
        # Find last sentence boundary (period, exclamation, question mark)
        last_period = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_period > 0:
            return truncated[:last_period + 1]
        else:
            # No sentence boundary found, just truncate with ellipsis
            return truncated.rstrip() + "..."
    
    def store_summary_cache(
        self,
        patient_id: int,
        visit_id: int,
        summary_entries: List[Dict]
    ) -> None:
        """
        Store retrieved summaries in cache for performance.
        
        Args:
            patient_id: Patient ID
            visit_id: Visit ID
            summary_entries: List of summary dicts from retrieve_and_summarize
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Insert or replace cache entries
        for entry in summary_entries:
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_summary_cache
                (patient_id, visit_id, doc_id, summary, similarity, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                patient_id,
                visit_id,
                entry['doc_id'],
                entry['summary'],
                entry['similarity']
            ))
        
        conn.commit()
        conn.close()
