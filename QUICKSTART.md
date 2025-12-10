# Quick Start Guide

## Installation

```bash
cd /Users/praneethkatakam/.gemini/antigravity/scratch/rag_causal_discovery

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Database is Already Seeded!

The database has been initialized with:
- ✅ 30 patients with realistic disease progressions
- ✅ 37 knowledge documents with real embeddings
- ✅ 21 disease transitions
- ✅ 20 co-occurrence relationships

## Start the API

```bash
uvicorn app:app --reload --port 8000
```

**Note**: First startup takes 10-20 seconds to load AI models.

## Test the System

### 1. Get Patients
```bash
curl http://127.0.0.1:8000/patients | python3 -m json.tool
```

### 2. Generate Prediction
```bash
curl -X POST "http://127.0.0.1:8000/agents/predict" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "clinician_comment": "Focus on kidney outcomes"}' \
  | python3 -m json.tool
```

### 3. Run Tests
```bash
pytest tests/ -v
```

## What Was Delivered

### Core Agents (930 LOC)
- `agents/knowledge_synthesis.py` - Semantic search with sentence-transformers
- `agents/causal_discovery.py` - DAG generation and refinement
- `agents/decision_making.py` - Flan-T5 ranking with fallback
- `agents/ollama_adapter.py` - Optional Ollama integration

### API Router (650 LOC)
- `api/agents_router.py` - 5 endpoints:
  - POST `/agents/predict` - Full agent workflow
  - POST `/agents/refine` - Clinician DAG editing
  - GET `/agents/dag/{patient_id}` - DAG retrieval
  - POST `/agents/upload_doc` - Document upload with PDF parsing
  - POST `/agents/chat` - Conversational AI

### Data Seeding (930 LOC)
- `scripts/seed_small.py` - 30 patients for development
- `scripts/seed_mimic_like.py` - ~5k patients with realistic patterns
- `scripts/db_compute_matrices.py` - Matrix recomputation

### Testing (755 LOC)
- `tests/test_agents.py` - 9 unit tests
- `tests/test_api.py` - 16 integration tests

### Total: 3,265 Lines of Production Code

## See Full Documentation

- `README.md` - Complete setup and API reference
- `walkthrough.md` - Implementation details and verification
