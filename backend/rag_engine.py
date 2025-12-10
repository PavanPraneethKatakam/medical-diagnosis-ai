import sqlite3
import json
import numpy as np

DB_PATH = "database/medical_knowledge.db"

class RAGEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def retrieve_knowledge(self, disease_codes):
        """
        Retrieves knowledge documents for a list of disease codes.
        In a real system, this would use vector similarity.
        For this MVP, we use exact matching on disease_code.
        """
        if not disease_codes:
            return []

        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?'] * len(disease_codes))
        query = f"""
            SELECT k.disease_code, k.section, k.content
            FROM knowledge_documents k
            WHERE k.disease_code IN ({placeholders})
        """
        
        cursor.execute(query, disease_codes)
        results = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in results:
            documents.append({
                "disease_code": row[0],
                "section": row[1],
                "content": row[2]
            })
            
        return documents

    def retrieve_similar_knowledge(self, query_embedding, top_k=3):
        """
        Mock vector search. In a real system, we'd compute cosine similarity
        between query_embedding and stored document_embeddings.
        """
        # For MVP, just return random documents associated with known diseases
        # This is a placeholder since we don't have a real embedding model running.
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT k.disease_code, k.section, k.content
            FROM knowledge_documents k
            ORDER BY RANDOM()
            LIMIT ?
        """, (top_k,))
        
        results = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in results:
            documents.append({
                "disease_code": row[0],
                "section": row[1],
                "content": row[2]
            })
            
        return documents
