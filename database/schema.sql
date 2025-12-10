-- Patients Table
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100),
    dob DATE,
    gender CHAR(1)
);

-- Visits Table
CREATE TABLE IF NOT EXISTS visits (
    visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_date DATE,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Diagnoses Table
CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL,
    disease_code VARCHAR(20),
    disease_name VARCHAR(255),
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
);

-- Disease Transition Matrix (renamed for clarity)
CREATE TABLE IF NOT EXISTS transition_matrix (
    from_disease VARCHAR(20) NOT NULL,
    to_disease VARCHAR(20) NOT NULL,
    transition_prob FLOAT,
    support_count INTEGER DEFAULT 0,
    PRIMARY KEY (from_disease, to_disease)
);

-- Keep old table name as view for backward compatibility
CREATE VIEW IF NOT EXISTS disease_transitions AS
SELECT from_disease, to_disease, transition_prob FROM transition_matrix;

-- Diagnosis Co-occurrence Matrix
CREATE TABLE IF NOT EXISTS diagnosis_matrix (
    disease_a VARCHAR(20) NOT NULL,
    disease_b VARCHAR(20) NOT NULL,
    co_occurrence_count INTEGER DEFAULT 0,
    total_patients INTEGER DEFAULT 0,
    PRIMARY KEY (disease_a, disease_b)
);

-- Chat Conversations
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    role TEXT CHECK(role IN ('user', 'assistant')),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Agent Memories (Clinician DAG Edits)
CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    dag_json TEXT,
    edit_action TEXT,
    edit_reason TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Knowledge Summary Cache
CREATE TABLE IF NOT EXISTS knowledge_summary_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_id INTEGER NOT NULL,
    doc_id INTEGER NOT NULL,
    summary TEXT,
    similarity FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id),
    FOREIGN KEY (doc_id) REFERENCES knowledge_documents(doc_id)
);

-- Knowledge Documents
CREATE TABLE IF NOT EXISTS knowledge_documents (
    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_code VARCHAR(20),
    section VARCHAR(50), -- e.g., "Symptoms", "Causes"
    content TEXT
);

-- Document Embeddings
-- SQLite has no native VECTOR type. Use JSON to store embeddings.
CREATE TABLE IF NOT EXISTS document_embeddings (
    doc_id INTEGER NOT NULL,
    embedding JSON, -- e.g., "[0.12, -0.34, ...]"
    PRIMARY KEY (doc_id),
    FOREIGN KEY (doc_id) REFERENCES knowledge_documents(doc_id)
);

-- Predictions
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_id INTEGER NOT NULL,
    predicted_disease_code VARCHAR(20),
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
);

-- Patient Documents (Health Reports)
CREATE TABLE IF NOT EXISTS patient_documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    document_type TEXT, -- 'lab_report', 'imaging', 'clinical_note'
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extracted_text TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);
