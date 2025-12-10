"""
Seed Small Dataset for Development

Creates a minimal dataset (~30 patients) for development and testing.
Generates real embeddings using sentence-transformers.
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer

DB_PATH = "database/medical_knowledge.db"
SCHEMA_PATH = "database/schema.sql"


def init_db():
    """Initialize database with schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized with new schema")


def seed_patients_and_visits():
    """Seed patients and their visit history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 30 realistic patients
    patients = [
        ("Sarah Martinez", "1957-03-15", "F"),
        ("James Chen", "1970-08-22", "M"),
        ("Maria Rodriguez", "1952-11-08", "F"),
        ("Robert Johnson", "1963-05-30", "M"),
        ("Linda Williams", "1966-02-14", "F"),
        ("Michael Brown", "1955-09-25", "M"),
        ("Patricia Davis", "1968-07-12", "F"),
        ("David Miller", "1959-12-03", "M"),
        ("Jennifer Garcia", "1972-04-18", "F"),
        ("Christopher Lee", "1961-10-27", "M"),
        ("Nancy Wilson", "1954-06-09", "F"),
        ("Daniel Moore", "1967-01-21", "M"),
        ("Lisa Taylor", "1969-11-15", "F"),
        ("Paul Anderson", "1958-08-07", "M"),
        ("Karen Thomas", "1971-03-29", "F"),
        ("Mark Jackson", "1956-12-11", "M"),
        ("Betty White", "1953-05-16", "F"),
        ("Steven Harris", "1965-09-23", "M"),
        ("Sandra Martin", "1974-02-08", "F"),
        ("Kevin Thompson", "1962-07-19", "M"),
        ("Emily Davis", "1968-11-30", "F"),
        ("Richard Wilson", "1960-04-25", "M"),
        ("Susan Moore", "1973-09-14", "F"),
        ("Thomas Anderson", "1957-06-08", "M"),
        ("Jessica Taylor", "1975-12-20", "F"),
        ("Charles Martinez", "1964-03-17", "M"),
        ("Margaret Brown", "1951-08-29", "F"),
        ("Joseph Garcia", "1969-01-11", "M"),
        ("Dorothy Johnson", "1956-10-05", "F"),
        ("William Lee", "1972-05-23", "M")
    ]
    
    cursor.executemany("INSERT INTO patients (name, dob, gender) VALUES (?, ?, ?)", patients)
    
    # Disease progressions
    progressions = [
        # Patient 1: HTN → CKD Stage 3 → CKD Stage 4
        (1, [
            ("2022-01-15", "I10", "Essential hypertension"),
            ("2023-03-20", "N18.3", "Chronic kidney disease, stage 3"),
            ("2024-01-10", "N18.4", "Chronic kidney disease, stage 4")
        ]),
        # Patient 2: T2DM → CAD → MI
        (2, [
            ("2021-06-10", "E11", "Type 2 diabetes mellitus"),
            ("2023-02-15", "I25.10", "Atherosclerotic heart disease"),
            ("2024-02-01", "I21.9", "Acute myocardial infarction")
        ]),
        # Patient 3: HTN + T2DM → CKD
        (3, [
            ("2020-05-12", "I10", "Essential hypertension"),
            ("2021-08-20", "E11", "Type 2 diabetes mellitus"),
            ("2023-06-15", "N18.3", "Chronic kidney disease, stage 3")
        ]),
        # Continue with more patients...
        (4, [("2022-03-10", "E66.9", "Obesity"), ("2023-07-15", "E11", "Type 2 diabetes mellitus")]),
        (5, [("2021-09-05", "J44.9", "COPD"), ("2023-11-20", "I27.0", "Pulmonary hypertension")]),
        (6, [("2020-02-18", "I10", "Essential hypertension"), ("2022-08-25", "I25.10", "CAD")]),
        (7, [("2022-11-12", "E11", "Type 2 diabetes mellitus")]),
        (8, [("2021-04-20", "I10", "Essential hypertension"), ("2023-09-15", "I63.9", "Stroke")]),
        (9, [("2023-01-08", "E11", "Type 2 diabetes mellitus")]),
        (10, [("2021-07-22", "I10", "Essential hypertension"), ("2023-10-20", "I25.10", "CAD")]),
        (11, [("2022-02-10", "N18.4", "CKD Stage 4"), ("2023-08-15", "D63.1", "Anemia in CKD")]),
        (12, [("2022-09-18", "E11", "Type 2 diabetes mellitus"), ("2024-01-05", "G63.2", "Diabetic neuropathy")]),
        (13, [("2023-03-25", "I10", "Essential hypertension")]),
        (14, [("2021-11-30", "I25.10", "CAD"), ("2022-06-15", "I25.2", "Old MI")]),
        (15, [("2022-05-20", "E11", "Type 2 diabetes mellitus"), ("2023-11-10", "I10", "HTN")]),
        (16, [("2021-08-14", "I10", "Essential hypertension"), ("2023-12-20", "N18.3", "CKD Stage 3")]),
        (17, [("2020-10-05", "I10", "HTN"), ("2021-04-12", "E11", "T2DM"), ("2023-07-25", "N18.3", "CKD Stage 3")]),
        (18, [("2022-01-28", "E11", "Type 2 diabetes mellitus"), ("2024-01-18", "I25.10", "CAD")]),
        (19, [("2023-06-10", "I10", "Essential hypertension")]),
        (20, [("2022-12-15", "I10", "Essential hypertension"), ("2024-02-05", "N18.2", "CKD Stage 2")]),
        (21, [("2021-03-10", "E11", "Type 2 diabetes mellitus"), ("2023-05-15", "N18.3", "CKD Stage 3")]),
        (22, [("2022-07-20", "I10", "Essential hypertension"), ("2023-09-10", "I50.9", "Heart failure")]),
        (23, [("2023-02-14", "E11", "Type 2 diabetes mellitus")]),
        (24, [("2021-11-05", "I10", "HTN"), ("2022-12-20", "I25.10", "CAD"), ("2024-01-15", "I21.9", "MI")]),
        (25, [("2023-08-18", "E66.9", "Obesity")]),
        (26, [("2020-06-12", "I10", "HTN"), ("2022-04-25", "N18.3", "CKD Stage 3"), ("2023-10-30", "I50.9", "HF")]),
        (27, [("2021-09-22", "E11", "T2DM"), ("2023-11-08", "H36.0", "Diabetic retinopathy")]),
        (28, [("2022-05-17", "J44.9", "COPD")]),
        (29, [("2020-12-01", "I10", "HTN"), ("2022-08-14", "I63.9", "Stroke")]),
        (30, [("2023-04-20", "E11", "Type 2 diabetes mellitus")])
    ]
    
    for patient_id, diagnoses in progressions:
        for visit_date, disease_code, disease_name in diagnoses:
            cursor.execute("INSERT INTO visits (patient_id, visit_date) VALUES (?, ?)", (patient_id, visit_date))
            visit_id = cursor.lastrowid
            cursor.execute("INSERT INTO diagnoses (visit_id, disease_code, disease_name) VALUES (?, ?, ?)", 
                         (visit_id, disease_code, disease_name))
    
    conn.commit()
    conn.close()
    print(f"✓ Seeded {len(patients)} patients with visit histories")


def seed_knowledge_documents():
    """Seed knowledge documents with real embeddings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    knowledge = [
        ('I10', 'Symptoms', 'Headaches, shortness of breath, nosebleeds, dizziness.'),
        ('I10', 'Causes', 'High salt intake, obesity, lack of exercise, genetics, stress.'),
        ('I10', 'Risk Factors', 'Hypertension is a major risk factor for chronic kidney disease and cardiovascular disease. Prolonged high blood pressure damages blood vessels in the kidneys, leading to CKD progression.'),
        ('E11', 'Symptoms', 'Increased thirst, frequent urination, hunger, fatigue, blurred vision.'),
        ('E11', 'Causes', 'Insulin resistance, genetics, obesity, sedentary lifestyle.'),
        ('E11', 'Complications', 'Type 2 diabetes causes microvascular damage and is associated with progression to chronic kidney disease, neuropathy, and cardiovascular disease.'),
        ('N18.9', 'Symptoms', 'Nausea, vomiting, loss of appetite, fatigue, sleep problems, decreased urine output.'),
        ('N18.9', 'Causes', 'Diabetes, high blood pressure, glomerulonephritis.'),
        ('N18.9', 'Progression', 'Chronic kidney disease leads to heart failure in many patients due to fluid overload and cardiovascular strain.'),
        ('N18.3', 'Symptoms', 'Fatigue, fluid retention, changes in urination.'),
        ('N18.3', 'Causes', 'Progression from earlier CKD stages, uncontrolled diabetes/hypertension.'),
        ('N18.4', 'Symptoms', 'Severe fatigue, fluid retention, nausea, confusion.'),
        ('N18.4', 'Causes', 'Advanced kidney damage from diabetes, hypertension.'),
        ('I25.10', 'Symptoms', 'Chest pain (angina), shortness of breath, fatigue.'),
        ('I25.10', 'Causes', 'Buildup of plaque in coronary arteries, atherosclerosis.'),
        ('I25.10', 'Risk', 'Coronary artery disease results in myocardial infarction and heart failure in high-risk patients.'),
        ('I50.9', 'Symptoms', 'Shortness of breath, fatigue, swollen legs, rapid heartbeat.'),
        ('I50.9', 'Causes', 'Coronary artery disease, high blood pressure, previous heart attack.'),
        ('I21.9', 'Symptoms', 'Severe chest pain, shortness of breath, sweating, nausea.'),
        ('I21.9', 'Causes', 'Complete blockage of coronary artery, blood clot.'),
        ('I21.9', 'Outcome', 'Acute myocardial infarction leads to heart failure with very high probability due to myocardial damage.'),
        ('J44.9', 'Symptoms', 'Chronic cough, wheezing, shortness of breath, chest tightness.'),
        ('J44.9', 'Causes', 'Smoking, air pollution, occupational dust exposure.'),
        ('I27.0', 'Symptoms', 'Shortness of breath, fatigue, chest pain, swelling in legs.'),
        ('I27.0', 'Causes', 'Lung disease, blood clots, congenital heart disease.'),
        ('G63.2', 'Symptoms', 'Numbness, tingling, pain in extremities.'),
        ('G63.2', 'Causes', 'Prolonged high blood sugar damaging nerves.'),
        ('I63.9', 'Symptoms', 'Sudden weakness, confusion, trouble speaking, vision problems.'),
        ('I63.9', 'Causes', 'Blood clot blocking brain artery, often from hypertension.'),
        ('H36.0', 'Symptoms', 'Blurred vision, floaters, vision loss.'),
        ('H36.0', 'Causes', 'Diabetes damaging blood vessels in retina.'),
        ('D63.1', 'Symptoms', 'Fatigue, weakness, pale skin.'),
        ('D63.1', 'Causes', 'Reduced erythropoietin production in chronic kidney disease.'),
        ('E66.9', 'Symptoms', 'Excess body weight, difficulty with physical activity.'),
        ('E66.9', 'Risk', 'Obesity is associated with development of type 2 diabetes mellitus.'),
        ('I25.2', 'Symptoms', 'May be asymptomatic or have chronic chest discomfort.'),
        ('I25.2', 'Causes', 'Previous myocardial infarction with healed scar tissue.')
    ]
    
    cursor.executemany("INSERT INTO knowledge_documents (disease_code, section, content) VALUES (?, ?, ?)", knowledge)
    conn.commit()
    
    # Generate real embeddings
    print("Generating embeddings with sentence-transformers...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    cursor.execute("SELECT doc_id, content FROM knowledge_documents")
    docs = cursor.fetchall()
    
    for doc_id, content in docs:
        embedding = model.encode(content, convert_to_numpy=True)
        cursor.execute("INSERT INTO document_embeddings (doc_id, embedding) VALUES (?, ?)", 
                     (doc_id, json.dumps(embedding.tolist())))
    
    conn.commit()
    conn.close()
    print(f"✓ Seeded {len(knowledge)} knowledge documents with embeddings")


def compute_matrices():
    """Compute transition_matrix and diagnosis_matrix from patient data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Compute transition matrix
    cursor.execute("""
        SELECT 
            d1.disease_code AS from_disease,
            d2.disease_code AS to_disease,
            COUNT(*) AS transition_count
        FROM diagnoses d1
        JOIN diagnoses d2 ON d1.visit_id < d2.visit_id
        JOIN visits v1 ON d1.visit_id = v1.visit_id
        JOIN visits v2 ON d2.visit_id = v2.visit_id
        WHERE v1.patient_id = v2.patient_id
        GROUP BY d1.disease_code, d2.disease_code
    """)
    
    transitions = cursor.fetchall()
    
    # Calculate probabilities
    from_disease_counts = {}
    for from_disease, to_disease, count in transitions:
        if from_disease not in from_disease_counts:
            from_disease_counts[from_disease] = 0
        from_disease_counts[from_disease] += count
    
    for from_disease, to_disease, count in transitions:
        total = from_disease_counts[from_disease]
        prob = count / total if total > 0 else 0
        cursor.execute("""
            INSERT INTO transition_matrix (from_disease, to_disease, transition_prob, support_count)
            VALUES (?, ?, ?, ?)
        """, (from_disease, to_disease, prob, count))
    
    print(f"✓ Computed transition matrix: {len(transitions)} transitions")
    
    # Compute diagnosis matrix (co-occurrences)
    cursor.execute("""
        SELECT 
            d1.disease_code AS disease_a,
            d2.disease_code AS disease_b,
            COUNT(DISTINCT v1.patient_id) AS co_occurrence_count
        FROM diagnoses d1
        JOIN diagnoses d2 ON d1.disease_code < d2.disease_code
        JOIN visits v1 ON d1.visit_id = v1.visit_id
        JOIN visits v2 ON d2.visit_id = v2.visit_id
        WHERE v1.patient_id = v2.patient_id
        GROUP BY d1.disease_code, d2.disease_code
    """)
    
    co_occurrences = cursor.fetchall()
    
    # Get total patients
    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]
    
    for disease_a, disease_b, count in co_occurrences:
        cursor.execute("""
            INSERT INTO diagnosis_matrix (disease_a, disease_b, co_occurrence_count, total_patients)
            VALUES (?, ?, ?, ?)
        """, (disease_a, disease_b, count, total_patients))
    
    conn.commit()
    conn.close()
    print(f"✓ Computed diagnosis matrix: {len(co_occurrences)} co-occurrences")


if __name__ == "__main__":
    print("Seeding small development database...")
    init_db()
    seed_patients_and_visits()
    seed_knowledge_documents()
    compute_matrices()
    print("\n✅ Database seeded successfully with 30 patients!")
    print("   Run: uvicorn app:app --reload --port 8000")
