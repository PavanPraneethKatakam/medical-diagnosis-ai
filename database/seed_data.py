import sqlite3
import json
import random
from datetime import datetime, timedelta

DB_PATH = "database/medical_knowledge.db"
SCHEMA_PATH = "database/schema.sql"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # MIMIC-inspired realistic patients
    patients = [
        ("Sarah Martinez", "1957-03-15", "F"),  # 67
        ("James Chen", "1970-08-22", "M"),      # 54
        ("Maria Rodriguez", "1952-11-08", "F"), # 72
        ("Robert Johnson", "1963-05-30", "M"),  # 61
        ("Linda Williams", "1966-02-14", "F"),  # 58
        ("Michael Brown", "1955-09-25", "M"),   # 69
        ("Patricia Davis", "1968-07-12", "F"),  # 56
        ("David Miller", "1959-12-03", "M"),    # 65
        ("Jennifer Garcia", "1972-04-18", "F"), # 52
        ("Christopher Lee", "1961-10-27", "M"), # 63
        ("Nancy Wilson", "1954-06-09", "F"),    # 70
        ("Daniel Moore", "1967-01-21", "M"),    # 57
        ("Lisa Taylor", "1969-11-15", "F"),     # 55
        ("Paul Anderson", "1958-08-07", "M"),   # 66
        ("Karen Thomas", "1971-03-29", "F"),    # 53
        ("Mark Jackson", "1956-12-11", "M"),    # 68
        ("Betty White", "1953-05-16", "F"),     # 71
        ("Steven Harris", "1965-09-23", "M"),   # 59
        ("Sandra Martin", "1974-02-08", "F"),   # 50
        ("Kevin Thompson", "1962-07-19", "M")   # 62
    ]
    cursor.executemany("INSERT INTO patients (name, dob, gender) VALUES (?, ?, ?)", patients)

    # Disease progressions based on MIMIC patterns
    progressions = [
        # Patient 1: Sarah Martinez - HTN → CKD Stage 3 → CKD Stage 4 (High risk HF)
        (1, [
            ("2022-01-15", "I10", "Essential hypertension"),
            ("2023-03-20", "N18.3", "Chronic kidney disease, stage 3"),
            ("2024-01-10", "N18.4", "Chronic kidney disease, stage 4")
        ]),
        # Patient 2: James Chen - T2DM → CAD → Recent MI (Very high risk HF)
        (2, [
            ("2021-06-10", "E11", "Type 2 diabetes mellitus"),
            ("2023-02-15", "I25.10", "Atherosclerotic heart disease"),
            ("2024-02-01", "I21.9", "Acute myocardial infarction")
        ]),
        # Patient 3: Maria Rodriguez - HTN + T2DM → CKD + Retinopathy (High risk ESRD)
        (3, [
            ("2020-05-12", "I10", "Essential hypertension"),
            ("2021-08-20", "E11", "Type 2 diabetes mellitus"),
            ("2023-06-15", "N18.3", "Chronic kidney disease, stage 3"),
            ("2024-01-20", "H36.0", "Diabetic retinopathy")
        ]),
        # Patient 4: Robert Johnson - Obesity → T2DM → Neuropathy (Moderate risk CAD)
        (4, [
            ("2022-03-10", "E66.9", "Obesity, unspecified"),
            ("2023-07-15", "E11", "Type 2 diabetes mellitus"),
            ("2024-02-10", "G63.2", "Diabetic polyneuropathy")
        ]),
        # Patient 5: Linda Williams - Smoking → COPD → Pulmonary HTN (High risk RHF)
        (5, [
            ("2021-09-05", "J44.9", "Chronic obstructive pulmonary disease"),
            ("2023-11-20", "I27.0", "Primary pulmonary hypertension")
        ]),
        # Patient 6: Michael Brown - HTN → CAD → Stable angina
        (6, [
            ("2020-02-18", "I10", "Essential hypertension"),
            ("2022-08-25", "I25.10", "Atherosclerotic heart disease"),
            ("2023-12-10", "I20.9", "Angina pectoris, unspecified")
        ]),
        # Patient 7: Patricia Davis - T2DM → Early CKD
        (7, [
            ("2022-11-12", "E11", "Type 2 diabetes mellitus"),
            ("2024-01-15", "N18.2", "Chronic kidney disease, stage 2")
        ]),
        # Patient 8: David Miller - HTN → Stroke → Recovery
        (8, [
            ("2021-04-20", "I10", "Essential hypertension"),
            ("2023-09-15", "I63.9", "Cerebral infarction, unspecified")
        ]),
        # Patient 9: Jennifer Garcia - T2DM → Well controlled
        (9, [
            ("2023-01-08", "E11", "Type 2 diabetes mellitus")
        ]),
        # Patient 10: Christopher Lee - HTN + Hyperlipidemia → CAD
        (10, [
            ("2021-07-22", "I10", "Essential hypertension"),
            ("2022-03-15", "E78.5", "Hyperlipidemia, unspecified"),
            ("2023-10-20", "I25.10", "Atherosclerotic heart disease")
        ]),
        # Patient 11: Nancy Wilson - CKD Stage 4 → Anemia (Very high risk HF)
        (11, [
            ("2022-02-10", "N18.4", "Chronic kidney disease, stage 4"),
            ("2023-08-15", "D63.1", "Anemia in chronic kidney disease")
        ]),
        # Patient 12: Daniel Moore - T2DM → Peripheral neuropathy
        (12, [
            ("2022-09-18", "E11", "Type 2 diabetes mellitus"),
            ("2024-01-05", "G63.2", "Diabetic polyneuropathy")
        ]),
        # Patient 13: Lisa Taylor - HTN → Early CKD
        (13, [
            ("2023-03-25", "I10", "Essential hypertension"),
            ("2024-02-12", "N18.2", "Chronic kidney disease, stage 2")
        ]),
        # Patient 14: Paul Anderson - CAD → Previous MI → Stable
        (14, [
            ("2021-11-30", "I25.10", "Atherosclerotic heart disease"),
            ("2022-06-15", "I25.2", "Old myocardial infarction")
        ]),
        # Patient 15: Karen Thomas - T2DM → HTN
        (15, [
            ("2022-05-20", "E11", "Type 2 diabetes mellitus"),
            ("2023-11-10", "I10", "Essential hypertension")
        ]),
        # Patient 16: Mark Jackson - HTN → CKD Stage 3
        (16, [
            ("2021-08-14", "I10", "Essential hypertension"),
            ("2023-12-20", "N18.3", "Chronic kidney disease, stage 3")
        ]),
        # Patient 17: Betty White - HTN + T2DM → CKD Stage 3
        (17, [
            ("2020-10-05", "I10", "Essential hypertension"),
            ("2021-04-12", "E11", "Type 2 diabetes mellitus"),
            ("2023-07-25", "N18.3", "Chronic kidney disease, stage 3")
        ]),
        # Patient 18: Steven Harris - T2DM → CAD
        (18, [
            ("2022-01-28", "E11", "Type 2 diabetes mellitus"),
            ("2024-01-18", "I25.10", "Atherosclerotic heart disease")
        ]),
        # Patient 19: Sandra Martin - HTN → Well controlled
        (19, [
            ("2023-06-10", "I10", "Essential hypertension")
        ]),
        # Patient 20: Kevin Thompson - HTN → CKD Stage 2
        (20, [
            ("2022-12-15", "I10", "Essential hypertension"),
            ("2024-02-05", "N18.2", "Chronic kidney disease, stage 2")
        ])
    ]

    for patient_id, diagnoses in progressions:
        for visit_date, disease_code, disease_name in diagnoses:
            cursor.execute("INSERT INTO visits (patient_id, visit_date) VALUES (?, ?)", (patient_id, visit_date))
            visit_id = cursor.lastrowid
            cursor.execute("INSERT INTO diagnoses (visit_id, disease_code, disease_name) VALUES (?, ?, ?)", 
                         (visit_id, disease_code, disease_name))

    # Disease Transitions (MIMIC-based probabilities)
    transitions = [
        ('I10', 'N18.9', 0.40),  # HTN → CKD
        ('I10', 'I25.10', 0.30), # HTN → CAD
        ('I10', 'I63.9', 0.15),  # HTN → Stroke
        ('E11', 'I25.10', 0.50), # T2DM → CAD
        ('E11', 'N18.9', 0.40),  # T2DM → CKD
        ('E11', 'G63.2', 0.35),  # T2DM → Neuropathy
        ('N18.9', 'I50.9', 0.60), # CKD → HF
        ('N18.3', 'I50.9', 0.50), # CKD Stage 3 → HF
        ('N18.4', 'I50.9', 0.75), # CKD Stage 4 → HF (higher risk)
        ('I25.10', 'I50.9', 0.50), # CAD → HF
        ('I25.10', 'I21.9', 0.30), # CAD → MI
        ('I21.9', 'I50.9', 0.80),  # MI → HF (very high)
        ('J44.9', 'I27.0', 0.45),  # COPD → Pulmonary HTN
        ('I27.0', 'I50.9', 0.70)   # Pulmonary HTN → RHF
    ]
    cursor.executemany("INSERT INTO disease_transitions (from_disease, to_disease, transition_prob) VALUES (?, ?, ?)", transitions)

    # Knowledge Documents (expanded)
    knowledge = [
        ('I10', 'Symptoms', 'Headaches, shortness of breath, nosebleeds, dizziness.'),
        ('I10', 'Causes', 'High salt intake, obesity, lack of exercise, genetics, stress.'),
        ('E11', 'Symptoms', 'Increased thirst, frequent urination, hunger, fatigue, blurred vision.'),
        ('E11', 'Causes', 'Insulin resistance, genetics, obesity, sedentary lifestyle.'),
        ('N18.9', 'Symptoms', 'Nausea, vomiting, loss of appetite, fatigue, sleep problems, decreased urine output.'),
        ('N18.9', 'Causes', 'Diabetes, high blood pressure, glomerulonephritis.'),
        ('N18.3', 'Symptoms', 'Fatigue, fluid retention, changes in urination.'),
        ('N18.3', 'Causes', 'Progression from earlier CKD stages, uncontrolled diabetes/hypertension.'),
        ('N18.4', 'Symptoms', 'Severe fatigue, fluid retention, nausea, confusion.'),
        ('N18.4', 'Causes', 'Advanced kidney damage from diabetes, hypertension.'),
        ('I25.10', 'Symptoms', 'Chest pain (angina), shortness of breath, fatigue.'),
        ('I25.10', 'Causes', 'Buildup of plaque in coronary arteries, atherosclerosis.'),
        ('I50.9', 'Symptoms', 'Shortness of breath, fatigue, swollen legs, rapid heartbeat.'),
        ('I50.9', 'Causes', 'Coronary artery disease, high blood pressure, previous heart attack.'),
        ('I21.9', 'Symptoms', 'Severe chest pain, shortness of breath, sweating, nausea.'),
        ('I21.9', 'Causes', 'Complete blockage of coronary artery, blood clot.'),
        ('J44.9', 'Symptoms', 'Chronic cough, wheezing, shortness of breath, chest tightness.'),
        ('J44.9', 'Causes', 'Smoking, air pollution, occupational dust exposure.'),
        ('I27.0', 'Symptoms', 'Shortness of breath, fatigue, chest pain, swelling in legs.'),
        ('I27.0', 'Causes', 'Lung disease, blood clots, congenital heart disease.'),
        ('G63.2', 'Symptoms', 'Numbness, tingling, pain in extremities.'),
        ('G63.2', 'Causes', 'Prolonged high blood sugar damaging nerves.')
    ]
    cursor.executemany("INSERT INTO knowledge_documents (disease_code, section, content) VALUES (?, ?, ?)", knowledge)

    # Document Embeddings
    cursor.execute("SELECT doc_id FROM knowledge_documents")
    doc_ids = cursor.fetchall()
    
    for doc_id in doc_ids:
        embedding = [round(random.uniform(-1, 1), 2) for _ in range(5)]
        cursor.execute("INSERT INTO document_embeddings (doc_id, embedding) VALUES (?, ?)", 
                     (doc_id[0], json.dumps(embedding)))

    conn.commit()
    conn.close()
    print("Database seeded successfully with 20 MIMIC-inspired patients.")

if __name__ == "__main__":
    init_db()
    seed_data()
