import sqlite3
from PyPDF2 import PdfReader
import io

class DocumentProcessor:
    def __init__(self, db_path="database/rag_causal.db"):
        self.db_path = db_path
    
    def extract_text_from_pdf(self, file_bytes):
        """Extract text from PDF file bytes."""
        try:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def extract_text_from_file(self, file_bytes, filename):
        """Extract text based on file type."""
        if filename.lower().endswith('.pdf'):
            return self.extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith('.txt'):
            return file_bytes.decode('utf-8', errors='ignore')
        else:
            return file_bytes.decode('utf-8', errors='ignore')
    
    def parse_lab_values(self, text):
        """
        Simple heuristic to extract lab values from text.
        Returns a dict of key-value pairs.
        """
        lab_values = {}
        lines = text.split('\n')
        
        # Common lab test patterns
        keywords = ['glucose', 'hba1c', 'cholesterol', 'ldl', 'hdl', 'triglycerides', 
                   'creatinine', 'egfr', 'hemoglobin', 'wbc', 'platelets']
        
        for line in lines:
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower:
                    # Try to extract numeric value
                    parts = line.split(':')
                    if len(parts) >= 2:
                        lab_values[keyword] = parts[1].strip()
        
        return lab_values
    
    def store_document(self, patient_id, filename, file_bytes, document_type='lab_report'):
        """Store uploaded document in database."""
        extracted_text = self.extract_text_from_file(file_bytes, filename)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO patient_documents (patient_id, filename, document_type, extracted_text)
            VALUES (?, ?, ?, ?)
        """, (patient_id, filename, document_type, extracted_text))
        
        conn.commit()
        document_id = cursor.lastrowid
        conn.close()
        
        return {
            "document_id": document_id,
            "extracted_text": extracted_text,
            "lab_values": self.parse_lab_values(extracted_text)
        }
    
    def get_patient_documents(self, patient_id):
        """Retrieve all documents for a patient."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT document_id, filename, document_type, upload_date, extracted_text
            FROM patient_documents
            WHERE patient_id = ?
            ORDER BY upload_date DESC
        """, (patient_id,))
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                "document_id": row[0],
                "filename": row[1],
                "document_type": row[2],
                "upload_date": row[3],
                "extracted_text": row[4]
            })
        
        conn.close()
        return documents
