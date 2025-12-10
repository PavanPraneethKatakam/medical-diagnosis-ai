# Agentic Medical Diagnosis System

A comprehensive AI-powered medical diagnosis platform using multi-agent workflows with **KnowledgeSynthesisAgent**, **CausalDiscoveryAgent**, and **DecisionMakingAgent**.

## Features

- **🤖 Three Specialized AI Agents**:
  - **KnowledgeSynthesisAgent**: Semantic search over medical documents using sentence-transformers
  - **CausalDiscoveryAgent**: DAG generation and iterative refinement with causal phrase detection
  - **DecisionMakingAgent**: Disease prediction ranking using Flan-T5 with deterministic fallback

- **📊 Comprehensive API**:
  - `/agents/predict`: Full agent workflow for disease prediction
  - `/agents/refine`: Clinician-in-the-loop DAG editing
  - `/agents/dag/{patient_id}`: DAG visualization data
  - `/agents/upload_doc`: PDF/text document upload with embedding generation
  - `/agents/chat`: Conversational AI for patient queries

- **💾 Enhanced Database**:
  - Transition matrix for disease progressions
  - Diagnosis co-occurrence matrix for fit scoring
  - Conversation history storage
  - Agent memory for clinician edits
  - Knowledge summary caching

- **🧪 Testing Infrastructure**:
  - Unit tests for all agent classes
  - API integration tests
  - ~5k synthetic MIMIC-like patient dataset

## Setup

### Prerequisites

- Python 3.10+
- CPU-based (no GPU required)

### Installation

```bash
# Clone or navigate to project directory
cd rag_causal_discovery

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

#### Option 1: Small Development Dataset (~30 patients)

```bash
python scripts/seed_small.py
```

**Output**:
```
Seeding small development database...
✓ Database initialized with new schema
✓ Seeded 30 patients with visit histories
Generating embeddings with sentence-transformers...
✓ Seeded 36 knowledge documents with embeddings
✓ Computed transition matrix: 45 transitions
✓ Computed diagnosis matrix: 120 co-occurrences

✅ Database seeded successfully with 30 patients!
   Run: uvicorn app:app --reload --port 8000
```

#### Option 2: Large MIMIC-like Dataset (~5k patients)

```bash
# Generate 5000 patients (takes 3-5 minutes)
python scripts/seed_mimic_like.py 5000

# Seed knowledge documents separately
python scripts/seed_small.py  # Run only the knowledge seeding part
```

**Output**:
```
Generating 5000 synthetic patients...
  Generated 500/5000 patients...
  Generated 1000/5000 patients...
  ...
✓ Generated 5000 patients with disease progressions
Computing transition matrix...
✓ Computed 287 transitions
Computing diagnosis matrix...
✓ Computed 456 co-occurrences
✓ Generated reports/top_transitions.json
✓ Generated reports/sample_timelines.json

✅ Database seeded successfully with 5000 patients!
```

#### Recompute Matrices (Optional)

```bash
python scripts/db_compute_matrices.py
```

## Running the API

```bash
uvicorn app:app --reload --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
Loading embedding model: all-MiniLM-L6-v2...
Embedding model loaded.
Loading SLM model: google/flan-t5-small on cpu...
SLM model loaded and cached.
INFO:     Application startup complete.
```

**Note**: First startup takes 10-20 seconds to load models. Subsequent requests are fast (~2-6s).

## API Usage Examples

### 1. Get All Patients

```bash
curl http://127.0.0.1:8000/patients
```

**Response**:
```json
[
  {
    "patient_id": 1,
    "name": "Sarah Martinez",
    "dob": "1957-03-15",
    "gender": "F"
  },
  ...
]
```

### 2. Get Patient History

```bash
curl http://127.0.0.1:8000/patients/1/history
```

**Response**:
```json
[
  {
    "visit_date": "2022-01-15",
    "disease_code": "I10",
    "disease_name": "Essential hypertension"
  },
  {
    "visit_date": "2023-03-20",
    "disease_code": "N18.3",
    "disease_name": "Chronic kidney disease, stage 3"
  },
  {
    "visit_date": "2024-01-10",
    "disease_code": "N18.4",
    "disease_name": "Chronic kidney disease, stage 4"
  }
]
```

### 3. Generate Prediction (Full Agent Workflow)

```bash
curl -X POST "http://127.0.0.1:8000/agents/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "clinician_comment": "Prioritize kidney outcomes."
  }'
```

**Response**:
```json
{
  "predictions": [
    {
      "code": "I50.9",
      "score": 0.782,
      "rank": 1,
      "transition_score": 0.75,
      "doc_similarity": 0.89,
      "clinician_boost": 0.2
    },
    {
      "code": "D63.1",
      "score": 0.654,
      "rank": 2,
      "transition_score": 0.45,
      "doc_similarity": 0.76,
      "clinician_boost": 0.0
    }
  ],
  "explanation": "Based on transition probability (0.75) and document evidence (0.89), I50.9 is the most likely progression. Clinician input considered: Prioritize kidney outcomes.",
  "evidence": [
    {
      "doc_id": 9,
      "disease_code": "N18.9",
      "snippet": "Chronic kidney disease leads to heart failure in many patients due to fluid overload and cardiovascular strain.",
      "similarity": 0.89
    }
  ],
  "dag": {
    "nodes": [
      {"id": "N18.4"},
      {"id": "I50.9"},
      {"id": "D63.1"}
    ],
    "edges": [
      {
        "from": "N18.4",
        "to": "I50.9",
        "weight": 0.75,
        "fit_score": -2.3
      }
    ],
    "global_fit": -2.3,
    "modification_history": [
      {
        "iteration": 0,
        "edge": "N18.4 -> I50.9",
        "reason": "Found causal phrase 'leads to' in n18.9 document",
        "old_weight": 0.75,
        "new_weight": 0.9
      }
    ]
  },
  "prediction_id": 1,
  "patient_id": 1,
  "fallback": true
}
```

### 4. Refine DAG with Clinician Feedback

```bash
curl -X POST "http://127.0.0.1:8000/agents/refine" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "feedback": {
      "action": "add_edge",
      "from": "N18.4",
      "to": "N18.5",
      "reason": "Clinician: Patient showing rapid CKD progression"
    }
  }'
```

**Response**:
```json
{
  "predictions": [...],
  "explanation": "...",
  "dag": {
    "nodes": [...],
    "edges": [
      {
        "from": "N18.4",
        "to": "N18.5",
        "weight": 0.8,
        "clinician_added": true,
        "reason": "Clinician: Patient showing rapid CKD progression"
      }
    ]
  }
}
```

### 5. Get Latest DAG

```bash
curl http://127.0.0.1:8000/agents/dag/1
```

**Response**:
```json
{
  "patient_id": 1,
  "dag": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 6. Upload Medical Document

```bash
curl -X POST "http://127.0.0.1:8000/agents/upload_doc" \
  -F "file=@report.pdf" \
  -F "disease_code=I50.9"
```

**Response**:
```json
{
  "message": "Document uploaded successfully. Created 3 chunks.",
  "doc_ids": [37, 38, 39],
  "preview_snippets": [
    {
      "doc_id": 37,
      "preview": "Patient presents with shortness of breath and bilateral leg edema. Echocardiogram shows reduced ejection fraction of 35%. Diagnosis: Heart failure..."
    }
  ],
  "filename": "report.pdf",
  "disease_code": "I50.9"
}
```

### 7. Chat with AI

```bash
curl -X POST "http://127.0.0.1:8000/agents/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "message": "What should I watch for next?"
  }'
```

**Response**:
```json
{
  "reply": "Based on your current CKD stage 4 diagnosis, you should monitor for signs of heart failure such as shortness of breath, leg swelling, and fatigue. Regular follow-up with nephrology is recommended.",
  "conversation_id": 1,
  "patient_id": 1
}
```

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

**Expected Output**:
```
tests/test_agents.py::TestKnowledgeSynthesisAgent::test_generate_query PASSED
tests/test_agents.py::TestKnowledgeSynthesisAgent::test_retrieve_and_summarize PASSED
tests/test_agents.py::TestCausalDiscoveryAgent::test_build_candidate_set PASSED
tests/test_agents.py::TestCausalDiscoveryAgent::test_generate_initial_dag PASSED
tests/test_agents.py::TestDecisionMakingAgent::test_rank_and_explain_structure PASSED
tests/test_api.py::TestBasicEndpoints::test_get_patients PASSED
tests/test_api.py::TestAgentsPredictEndpoint::test_predict_success PASSED
...
======================== 18 passed in 45.2s ========================
```

### Unit Tests Only

```bash
pytest tests/test_agents.py -v
```

### API Tests Only

```bash
pytest tests/test_api.py -v
```

### With Coverage

```bash
pytest tests/ --cov=agents --cov=api --cov-report=html
```

## Smoke Test Checklist

| # | Command | Expected Output |
|---|---------|----------------|
| 1 | `python scripts/seed_small.py` | "✅ Database seeded successfully with 30 patients!" |
| 2 | `uvicorn app:app --port 8000` | "Application startup complete." |
| 3 | `curl http://127.0.0.1:8000/patients` | JSON array with 30 patients |
| 4 | `curl http://127.0.0.1:8000/patients/1/history` | JSON array with 3 diagnoses |
| 5 | `curl -X POST http://127.0.0.1:8000/agents/predict -H "Content-Type: application/json" -d '{"patient_id":1}'` | JSON with `predictions`, `explanation`, `dag` keys |
| 6 | `sqlite3 database/medical_knowledge.db "SELECT COUNT(*) FROM predictions;"` | "1" |
| 7 | `pytest tests/ -q` | "18 passed in Xs" |

## Project Structure

```
rag_causal_discovery/
├── agents/                      # Core agent modules
│   ├── __init__.py
│   ├── knowledge_synthesis.py  # Semantic search & summarization
│   ├── causal_discovery.py     # DAG generation & refinement
│   ├── decision_making.py      # Flan-T5 ranking & explanation
│   └── ollama_adapter.py       # Optional Ollama integration
├── api/                         # API routers
│   ├── __init__.py
│   └── agents_router.py        # All /agents/* endpoints
├── database/                    # Database files
│   ├── schema.sql              # Enhanced schema with new tables
│   └── medical_knowledge.db    # SQLite database
├── scripts/                     # Data seeding scripts
│   ├── seed_small.py           # 30 patients for development
│   ├── seed_mimic_like.py      # ~5k patients with realistic patterns
│   └── db_compute_matrices.py  # Recompute matrices
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_agents.py          # Unit tests for agents
│   └── test_api.py             # API integration tests
├── reports/                     # Generated reports (from seed_mimic_like.py)
│   ├── top_transitions.json
│   └── sample_timelines.json
├── app.py                       # Main FastAPI application
└── requirements.txt             # Python dependencies
```

## Architecture

### Agent Workflow

```
1. Patient History Retrieval
   ↓
2. Candidate Set Building (CausalDiscoveryAgent)
   ↓
3. Knowledge Retrieval (KnowledgeSynthesisAgent)
   ├─ Generate query from history + candidates
   ├─ Compute embeddings
   └─ Retrieve top-k documents with cosine similarity
   ↓
4. DAG Generation & Refinement (CausalDiscoveryAgent)
   ├─ Generate initial DAG from transition matrix
   ├─ Compute fit scores using diagnosis matrix
   └─ Iteratively refine using causal phrases from documents
   ↓
5. Ranking & Explanation (DecisionMakingAgent)
   ├─ Try Flan-T5 with strict JSON prompt
   ├─ Parse JSON with fallback strategies
   └─ If fails: deterministic ranking (0.6*transition + 0.3*similarity + 0.1*clinician)
   ↓
6. Store Prediction & Return Results
```

### Database Schema

**Core Tables**:
- `patients`, `visits`, `diagnoses`: Patient data
- `knowledge_documents`, `document_embeddings`: Medical knowledge with embeddings
- `transition_matrix`: Disease progression probabilities
- `diagnosis_matrix`: Co-occurrence statistics
- `predictions`: Stored prediction results
- `conversations`: Chat history
- `agent_memories`: Clinician DAG edits
- `knowledge_summary_cache`: Performance optimization

## Configuration

### Environment Variables

- `OLLAMA_ENABLED`: Set to `"true"` to use Ollama instead of Flan-T5 (default: `"false"`)

### Model Configuration

Models are cached as module-level singletons:
- **Embedding Model**: `all-MiniLM-L6-v2` (384-dimensional)
- **SLM Model**: `google/flan-t5-small` (60M parameters, CPU-optimized)

## Performance

- **First Request**: 10-20s (model loading)
- **Subsequent Requests**: 2-6s on CPU
- **Database Size**: ~50MB (30 patients), ~500MB (5k patients)
- **Memory Usage**: ~2GB RAM (models loaded)

## Troubleshooting

### "No module named 'sentence_transformers'"

```bash
pip install sentence-transformers
```

### "Database is locked"

Close any open database connections or SQLite browsers.

### "Model loading timeout"

First request may take longer. Increase timeout or pre-warm models:

```python
# In app.py startup event
from agents import get_agents
get_agents()  # Pre-load models
```

### Tests failing with "Database not found"

Run `python scripts/seed_small.py` before running tests.

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass: `pytest tests/ -v`
5. Submit a pull request

## Citation

If you use this system in your research, please cite:

```bibtex
@software{agentic_medical_diagnosis,
  title={Agentic Medical Diagnosis System},
  author=Pavan Praneeth Katakam,
  year= 2025,
  url={https://github.com/pavanpraneethkatakam/rag_causal_discovery}
}
```
