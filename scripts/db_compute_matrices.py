"""
Compute or Recompute Matrices from Existing Patient Data

This script can be run independently to recompute transition_matrix
and diagnosis_matrix from existing patient visit/diagnosis data.
"""

import sqlite3

DB_PATH = "database/medical_knowledge.db"


def compute_transition_matrix():
    """Compute transition matrix from patient visit sequences."""
    print("Computing transition matrix...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM transition_matrix")
    
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
          AND d1.disease_code != d2.disease_code
        GROUP BY d1.disease_code, d2.disease_code
    """)
    
    transitions = cursor.fetchall()
    
    if not transitions:
        print("WARNING: No transitions found. Make sure patient data is seeded.")
        conn.close()
        return
    
    # Calculate probabilities
    from_disease_counts = {}
    for from_disease, to_disease, count in transitions:
        if from_disease not in from_disease_counts:
            from_disease_counts[from_disease] = 0
        from_disease_counts[from_disease] += count
    
    # Insert with probabilities
    for from_disease, to_disease, count in transitions:
        total = from_disease_counts[from_disease]
        prob = count / total if total > 0 else 0
        cursor.execute("""
            INSERT INTO transition_matrix (from_disease, to_disease, transition_prob, support_count)
            VALUES (?, ?, ?, ?)
        """, (from_disease, to_disease, prob, count))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Computed {len(transitions)} transitions")
    
    # Print top transitions
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT from_disease, to_disease, transition_prob, support_count
        FROM transition_matrix
        ORDER BY transition_prob DESC
        LIMIT 10
    """)
    
    print("\nTop 10 transitions:")
    for row in cursor.fetchall():
        print(f"  {row[0]} → {row[1]}: {row[2]:.3f} (n={row[3]})")
    
    conn.close()


def compute_diagnosis_matrix():
    """Compute diagnosis co-occurrence matrix."""
    print("\nComputing diagnosis matrix...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM diagnosis_matrix")
    
    # Compute co-occurrences
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
    
    if not co_occurrences:
        print("WARNING: No co-occurrences found.")
        conn.close()
        return
    
    # Get total patients
    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]
    
    # Insert co-occurrences
    for disease_a, disease_b, count in co_occurrences:
        cursor.execute("""
            INSERT INTO diagnosis_matrix (disease_a, disease_b, co_occurrence_count, total_patients)
            VALUES (?, ?, ?, ?)
        """, (disease_a, disease_b, count, total_patients))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Computed {len(co_occurrences)} co-occurrences")
    
    # Print top co-occurrences
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT disease_a, disease_b, co_occurrence_count, total_patients
        FROM diagnosis_matrix
        ORDER BY co_occurrence_count DESC
        LIMIT 10
    """)
    
    print("\nTop 10 co-occurrences:")
    for row in cursor.fetchall():
        pct = (row[2] / row[3] * 100) if row[3] > 0 else 0
        print(f"  {row[0]} + {row[1]}: {row[2]} patients ({pct:.1f}%)")
    
    conn.close()


if __name__ == "__main__":
    print("Recomputing matrices from patient data...\n")
    compute_transition_matrix()
    compute_diagnosis_matrix()
    print("\n✅ Matrices computed successfully!")
