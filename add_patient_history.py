#!/usr/bin/env python3
"""
Add medical history for patients 31-90
Creates realistic disease progressions with visits and diagnoses
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "database/medical_knowledge.db"

# Disease progression patterns for different patient profiles
DISEASE_PROGRESSIONS = {
    "diabetes_progression": [
        ("E11", "Type 2 diabetes mellitus"),
        ("E11.9", "Type 2 diabetes without complications"),
        ("E11.65", "Type 2 diabetes with hyperglycemia"),
        ("E11.21", "Type 2 diabetes with diabetic nephropathy"),
        ("E11.22", "Type 2 diabetes with diabetic chronic kidney disease")
    ],
    "cardiac_progression": [
        ("I10", "Essential hypertension"),
        ("I25.10", "Atherosclerotic heart disease"),
        ("I50.9", "Heart failure, unspecified"),
        ("I50.23", "Acute on chronic systolic heart failure")
    ],
    "respiratory_progression": [
        ("J44.0", "COPD with acute lower respiratory infection"),
        ("J44.1", "COPD with acute exacerbation"),
        ("J44.9", "COPD"),
        ("J96.01", "Acute respiratory failure with hypoxia")
    ],
    "renal_progression": [
        ("N18.1", "Chronic kidney disease, stage 1"),
        ("N18.2", "Chronic kidney disease, stage 2"),
        ("N18.3", "Chronic kidney disease, stage 3"),
        ("N18.4", "Chronic kidney disease, stage 4"),
        ("N18.5", "Chronic kidney disease, stage 5")
    ],
    "obesity_metabolic": [
        ("E66.9", "Obesity"),
        ("E78.5", "Hyperlipidemia"),
        ("E11", "Type 2 diabetes mellitus"),
        ("I10", "Essential hypertension")
    ],
    "liver_progression": [
        ("K70.30", "Alcoholic cirrhosis of liver without ascites"),
        ("K70.31", "Alcoholic cirrhosis of liver with ascites"),
        ("K72.90", "Hepatic failure, unspecified"),
    ],
    "cancer_progression": [
        ("C34.90", "Malignant neoplasm of unspecified part of bronchus or lung"),
        ("C78.00", "Secondary malignant neoplasm of unspecified lung"),
        ("C79.51", "Secondary malignant neoplasm of bone")
    ]
}

def add_patient_history(patient_id, progression_type, start_date_str):
    """Add medical history for a patient with a specific disease progression"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    progression = DISEASE_PROGRESSIONS[progression_type]
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    
    # Create visits with increasing time intervals
    time_intervals = [0, 180, 365, 545, 730]  # Days between visits
    
    for i, (disease_code, disease_name) in enumerate(progression):
        if i >= len(time_intervals):
            break
            
        visit_date = start_date + timedelta(days=time_intervals[i])
        visit_date_str = visit_date.strftime("%Y-%m-%d")
        
        # Insert visit
        cursor.execute("""
            INSERT INTO visits (patient_id, visit_date)
            VALUES (?, ?)
        """, (patient_id, visit_date_str))
        
        visit_id = cursor.lastrowid
        
        # Insert diagnosis
        cursor.execute("""
            INSERT INTO diagnoses (visit_id, disease_code, disease_name)
            VALUES (?, ?, ?)
        """, (visit_id, disease_code, disease_name))
    
    conn.commit()
    conn.close()
    print(f"✅ Added {len(progression)} visits for patient {patient_id} ({progression_type})")

def main():
    print("Adding medical history for patients 31-90...")
    print("")
    
    # Assign different disease progressions to different patient groups
    assignments = [
        # Patients 31-40: Diabetes progression
        *[(pid, "diabetes_progression", "2019-01-15") for pid in range(31, 41)],
        # Patients 41-50: Cardiac progression
        *[(pid, "cardiac_progression", "2019-03-20") for pid in range(41, 51)],
        # Patients 51-60: Respiratory progression
        *[(pid, "respiratory_progression", "2019-06-10") for pid in range(51, 61)],
        # Patients 61-70: Renal progression
        *[(pid, "renal_progression", "2019-09-05") for pid in range(61, 71)],
        # Patients 71-80: Obesity/Metabolic
        *[(pid, "obesity_metabolic", "2020-01-12") for pid in range(71, 81)],
        # Patients 81-85: Liver progression
        *[(pid, "liver_progression", "2020-04-18") for pid in range(81, 86)],
        # Patients 86-90: Cancer progression
        *[(pid, "cancer_progression", "2020-07-22") for pid in range(86, 91)],
    ]
    
    for patient_id, progression_type, start_date in assignments:
        add_patient_history(patient_id, progression_type, start_date)
    
    print("")
    print("=" * 60)
    print("✅ Successfully added medical history for 60 patients (31-90)")
    print("=" * 60)
    
    # Verify
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT v.patient_id) 
        FROM visits v 
        WHERE v.patient_id BETWEEN 31 AND 90
    """)
    count = cursor.fetchone()[0]
    print(f"Patients with history: {count}/60")
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM visits v 
        WHERE v.patient_id BETWEEN 31 AND 90
    """)
    visit_count = cursor.fetchone()[0]
    print(f"Total visits added: {visit_count}")
    
    conn.close()

if __name__ == "__main__":
    main()
