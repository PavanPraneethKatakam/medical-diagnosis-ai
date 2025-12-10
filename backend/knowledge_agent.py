import sqlite3
import json

DB_PATH = "database/medical_knowledge.db"

class KnowledgeSynthesisAgent:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def synthesize_knowledge(self, disease_codes):
        """
        Retrieves relevant documents and synthesizes a summary.
        """
        if not disease_codes:
            return {"summary": "No relevant diseases identified for knowledge retrieval.", "documents": []}

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
        summary_lines = []
        
        for row in results:
            doc = {
                "disease_code": row[0],
                "section": row[1],
                "content": row[2]
            }
            documents.append(doc)
            summary_lines.append(f"- {row[0]} ({row[1]}): {row[2]}")
            
        summary = "Synthesized Medical Knowledge:\n" + "\n".join(summary_lines)
        
        return {
            "summary": summary,
            "documents": documents
        }
