"""
Seed MIMIC-like Dataset with ~5k Patients

Generates synthetic patient data with realistic disease prevalence and progression patterns.
Computes transition and diagnosis matrices, and generates reports.
"""

import sqlite3
import json
import random
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import os

DB_PATH = "database/medical_knowledge.db"
SCHEMA_PATH = "database/schema.sql"
REPORTS_DIR = "reports"

# Disease prevalence (approximate MIMIC-III distributions)
DISEASE_PREVALENCE = {
    "I10": 0.35,      # Hypertension
    "E11": 0.28,      # Type 2 Diabetes
    "I50.9": 0.15,    # Heart Failure
    "N18.9": 0.12,    # CKD
    "I25.10": 0.18,   # CAD
    "J44.9": 0.08,    # COPD
    "E66.9": 0.22,    # Obesity
}

# Progression patterns (from_disease -> [(to_disease, probability, avg_days)])
PROGRESSION_PATTERNS = {
    "I10": [("N18.9", 0.40, 730), ("I25.10", 0.30, 900), ("I63.9", 0.15, 1095)],
    "E11": [("I25.10", 0.50, 800), ("N18.9", 0.40, 850), ("G63.2", 0.35, 600), ("H36.0", 0.25, 700)],
    "N18.9": [("I50.9", 0.60, 500), ("D63.1", 0.45, 400)],
    "N18.3": [("N18.4", 0.50, 600), ("I50.9", 0.45, 700)],
    "N18.4": [("I50.9", 0.75, 400), ("N18.5", 0.60, 500)],
    "I25.10": [("I21.9", 0.30, 600), ("I50.9", 0.50, 800)],
    "I21.9": [("I50.9", 0.80, 180)],
    "J44.9": [("I27.0", 0.45, 900)],
    "I27.0": [("I50.9", 0.70, 600)],
    "E66.9": [("E11", 0.50, 1000), ("I10", 0.40, 900)],
}


def generate_name(gender):
    """Generate random patient name."""
    first_names_m = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    first_names_f = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    
    first = random.choice(first_names_m if gender == "M" else first_names_f)
    last = random.choice(last_names)
    return f"{first} {last}"


def generate_dob():
    """Generate date of birth (age 50-85)."""
    age = random.randint(50, 85)
    dob = datetime.now() - timedelta(days=age*365)
    return dob.strftime("%Y-%m-%d")


def generate_patient_progression(patient_id, start_date):
    """Generate disease progression for a patient."""
    # Start with a primary disease
    primary_disease = random.choices(
        list(DISEASE_PREVALENCE.keys()),
        weights=list(DISEASE_PREVALENCE.values())
    )[0]
    
    progression = [(start_date, primary_disease)]
    current_diseases = {primary_disease}
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Generate progression over 2-4 years
    max_visits = random.randint(2, 6)
    
    for _ in range(max_visits - 1):
        # Check if any current disease can progress
        possible_progressions = []
        for disease in current_diseases:
            if disease in PROGRESSION_PATTERNS:
                for next_disease, prob, avg_days in PROGRESSION_PATTERNS[disease]:
                    if next_disease not in current_diseases and random.random() < prob:
                        days_offset = int(np.random.normal(avg_days, avg_days * 0.2))
                        possible_progressions.append((next_disease, days_offset))
        
        if not possible_progressions:
            break
        
        # Pick one progression
        next_disease, days_offset = random.choice(possible_progressions)
        current_date += timedelta(days=max(30, days_offset))
        
        if current_date > datetime.now():
            break
        
        progression.append((current_date.strftime("%Y-%m-%d"), next_disease))
        current_diseases.add(next_disease)
    
    return progression


def seed_large_dataset(num_patients=5000):
    """Seed large dataset with num_patients."""
    print(f"Generating {num_patients} synthetic patients...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Initialize schema
    with open(SCHEMA_PATH, 'r') as f:
        cursor.executescript(f.read())
    
    # Disease code to name mapping
    disease_names = {
        "I10": "Essential hypertension",
        "E11": "Type 2 diabetes mellitus",
        "I50.9": "Heart failure, unspecified",
        "N18.9": "Chronic kidney disease, unspecified",
        "N18.3": "Chronic kidney disease, stage 3",
        "N18.4": "Chronic kidney disease, stage 4",
        "N18.5": "Chronic kidney disease, stage 5",
        "I25.10": "Atherosclerotic heart disease",
        "I21.9": "Acute myocardial infarction",
        "J44.9": "Chronic obstructive pulmonary disease",
        "I27.0": "Primary pulmonary hypertension",
        "E66.9": "Obesity, unspecified",
        "G63.2": "Diabetic polyneuropathy",
        "H36.0": "Diabetic retinopathy",
        "I63.9": "Cerebral infarction, unspecified",
        "D63.1": "Anemia in chronic kidney disease",
        "I25.2": "Old myocardial infarction"
    }
    
    # Generate patients
    for i in range(1, num_patients + 1):
        gender = random.choice(["M", "F"])
        name = generate_name(gender)
        dob = generate_dob()
        
        cursor.execute("INSERT INTO patients (name, dob, gender) VALUES (?, ?, ?)", (name, dob, gender))
        patient_id = cursor.lastrowid
        
        # Generate progression
        start_year = random.randint(2019, 2022)
        start_month = random.randint(1, 12)
        start_date = f"{start_year}-{start_month:02d}-{random.randint(1, 28):02d}"
        
        progression = generate_patient_progression(patient_id, start_date)
        
        for visit_date, disease_code in progression:
            cursor.execute("INSERT INTO visits (patient_id, visit_date) VALUES (?, ?)", (patient_id, visit_date))
            visit_id = cursor.lastrowid
            disease_name = disease_names.get(disease_code, "Unknown disease")
            cursor.execute("INSERT INTO diagnoses (visit_id, disease_code, disease_name) VALUES (?, ?, ?)",
                         (visit_id, disease_code, disease_name))
        
        if i % 500 == 0:
            conn.commit()
            print(f"  Generated {i}/{num_patients} patients...")
    
    conn.commit()
    conn.close()
    print(f"✓ Generated {num_patients} patients with disease progressions")


def compute_matrices():
    """Compute transition and diagnosis matrices."""
    print("Computing transition matrix...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Compute transitions
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
    
    conn.commit()
    print(f"✓ Computed {len(transitions)} transitions")
    
    # Compute diagnosis matrix
    print("Computing diagnosis matrix...")
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
    
    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]
    
    for disease_a, disease_b, count in co_occurrences:
        cursor.execute("""
            INSERT INTO diagnosis_matrix (disease_a, disease_b, co_occurrence_count, total_patients)
            VALUES (?, ?, ?, ?)
        """, (disease_a, disease_b, count, total_patients))
    
    conn.commit()
    conn.close()
    print(f"✓ Computed {len(co_occurrences)} co-occurrences")


def generate_reports():
    """Generate JSON reports."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Top transitions
    cursor.execute("""
        SELECT from_disease, to_disease, transition_prob, support_count
        FROM transition_matrix
        ORDER BY transition_prob DESC
        LIMIT 50
    """)
    
    top_transitions = [
        {
            "from": row[0],
            "to": row[1],
            "probability": round(row[2], 3),
            "support": row[3]
        }
        for row in cursor.fetchall()
    ]
    
    with open(f"{REPORTS_DIR}/top_transitions.json", "w") as f:
        json.dump(top_transitions, f, indent=2)
    
    print(f"✓ Generated {REPORTS_DIR}/top_transitions.json")
    
    # Sample timelines
    cursor.execute("""
        SELECT p.patient_id, p.name, v.visit_date, d.disease_code, d.disease_name
        FROM patients p
        JOIN visits v ON p.patient_id = v.patient_id
        JOIN diagnoses d ON v.visit_id = d.visit_id
        WHERE p.patient_id <= 10
        ORDER BY p.patient_id, v.visit_date
    """)
    
    timelines = {}
    for row in cursor.fetchall():
        patient_id, name, visit_date, disease_code, disease_name = row
        if patient_id not in timelines:
            timelines[patient_id] = {
                "patient_id": patient_id,
                "name": name,
                "timeline": []
            }
        timelines[patient_id]["timeline"].append({
            "date": visit_date,
            "code": disease_code,
            "name": disease_name
        })
    
    with open(f"{REPORTS_DIR}/sample_timelines.json", "w") as f:
        json.dump(list(timelines.values()), f, indent=2)
    
    print(f"✓ Generated {REPORTS_DIR}/sample_timelines.json")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    num_patients = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    
    print(f"Seeding MIMIC-like database with {num_patients} patients...")
    print("This may take several minutes...\n")
    
    seed_large_dataset(num_patients)
    compute_matrices()
    generate_reports()
    
    print(f"\n✅ Database seeded successfully with {num_patients} patients!")
    print("   Generated reports in reports/ directory")
    print("   Note: Knowledge documents should be seeded separately with seed_small.py")
