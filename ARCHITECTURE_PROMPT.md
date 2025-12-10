# Architecture Diagram Prompt for AI Medical Diagnosis System

## System Overview
Create a detailed architecture diagram for an AI-powered Medical Diagnosis System that uses a multi-agent workflow for disease prediction. The system combines RAG (Retrieval-Augmented Generation), causal discovery, and decision-making agents.

## Architecture Components

### 1. Frontend Layer (Client-Side)
- **Technology**: HTML5, CSS3 (Glassmorphism design), JavaScript
- **Components**:
  - Patient Selection Interface (dropdown with 90 patients)
  - Medical History Timeline Display
  - Prediction Results Cards (top 3 predictions with confidence scores)
  - Interactive DAG Visualization (Mermaid.js)
  - AI Chat Interface (conversational assistant)
  - Document Upload Form (PDF/text files)
  - Theme Toggle (dark mode)
- **Communication**: REST API calls to backend via fetch()

### 2. API Layer (FastAPI)
- **Main Application** (`app.py`):
  - Root endpoint: Serves frontend HTML
  - Static file serving: `/static/*` for CSS/JS
  - Health check: `/health`
  - Patient endpoints: `/patients`, `/patients/{id}/history`
  
- **Agents Router** (`/agents/*`):
  - `/agents/predict` - Generate disease predictions (POST)
  - `/agents/refine` - Refine DAG with clinician feedback (POST)
  - `/agents/chat` - AI assistant chat (POST)
  - `/agents/upload_doc` - Upload medical documents (POST)

- **Security Layer**:
  - HTTP Basic Authentication
  - Rate Limiting (100 req/min per IP)
  - Input Validation (Pydantic models)
  - File Upload Security (5MB max, .pdf/.txt only)

### 3. Multi-Agent System (Core Intelligence)

**Agent 1: Knowledge Synthesis Agent**
- **Purpose**: Retrieve and summarize relevant medical knowledge
- **Technology**: Sentence-BERT embeddings (all-MiniLM-L6-v2)
- **Process**:
  1. Generate search query from patient history
  2. Retrieve top-k similar documents from vector database
  3. Summarize findings using LLM
  4. Cache summaries for performance
- **Output**: List of relevant medical knowledge summaries

**Agent 2: Causal Discovery Agent**
- **Purpose**: Build causal relationship graphs (DAGs)
- **Technology**: PC algorithm, statistical analysis
- **Process**:
  1. Build candidate disease set from patient history
  2. Generate initial DAG structure
  3. Fit graph with patient data
  4. Apply clinician edits if provided
- **Output**: Directed Acyclic Graph (DAG) of disease relationships

**Agent 3: Decision Making Agent**
- **Purpose**: Rank diseases and generate explanations
- **Technology**: FLAN-T5 Small LLM with deterministic fallback
- **Process**:
  1. Receive patient summary, candidates, DAG, and knowledge
  2. Use LLM to rank diseases with reasoning
  3. Calculate composite scores (transition + DAG + knowledge)
  4. Generate natural language explanations
  5. Fallback to deterministic ranking if LLM fails
- **Output**: Ranked predictions with explanations and evidence

### 4. Model Pool (Singleton)
- **Purpose**: Centralized AI model management
- **Models**:
  - Embedding Model: sentence-transformers/all-MiniLM-L6-v2
  - LLM: google/flan-t5-small
- **Features**:
  - Lazy loading (load on first use)
  - Warmup inference at startup
  - Single instance shared across requests
  - Device management (CPU/GPU)

### 5. Database Layer (SQLite)
**Tables**:
- `patients` (90 patients with demographics)
- `visits` (424 patient visits)
- `diagnoses` (disease codes and names per visit)
- `predictions` (AI-generated predictions)
- `agent_memories` (persisted DAG states)
- `knowledge_summary_cache` (cached retrieval results)
- `conversations` (chat history)
- `medical_documents` (uploaded documents)
- `document_chunks` (chunked text with embeddings)

### 6. Data Flow

**Prediction Generation Flow**:
1. User selects patient → Frontend requests `/patients/{id}/history`
2. Frontend displays history → User clicks "Generate Prediction"
3. POST to `/agents/predict` with patient_id
4. Knowledge Agent retrieves relevant medical knowledge
5. Causal Agent builds/refines DAG from patient history
6. Decision Agent ranks diseases using all inputs
7. Results stored in database (predictions, agent_memories, cache)
8. Response returned to frontend with predictions, DAG, explanations
9. Frontend renders results (cards, DAG visualization, evidence)

**DAG Refinement Flow**:
1. Clinician provides feedback (add/remove/reverse edge)
2. POST to `/agents/refine` with feedback
3. Load existing DAG from agent_memories
4. Apply clinician edit to DAG
5. Re-rank predictions with updated DAG
6. Store updated DAG and new predictions
7. Return updated results to frontend

**Chat Flow**:
1. User sends message → POST to `/agents/chat`
2. Load conversation history from database
3. Generate context from patient history
4. LLM generates response
5. Store conversation in database
6. Return response to frontend

### 7. Key Features
- **Transaction Safety**: All database writes use context managers with auto-rollback
- **Caching**: Knowledge summaries cached per patient/visit
- **Agent Memory**: DAG states persisted and reused
- **Fallback Mechanisms**: Deterministic ranking when LLM fails
- **JSON Robustness**: 5-stage parsing pipeline with token cleaning
- **Performance**: Models preloaded at startup, <2s prediction time

### 8. Technology Stack
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **AI/ML**: Transformers, Sentence-Transformers, PyTorch
- **Database**: SQLite3 with transaction support
- **Frontend**: Vanilla JavaScript, CSS3, Mermaid.js
- **Security**: HTTP Basic Auth, Rate Limiting, Input Validation

### 9. Deployment
- **Development**: `uvicorn app:app --reload` (single worker)
- **Production**: `uvicorn app:app --workers 4` (multi-worker)
- **Port**: 8001
- **Static Files**: Served from `/static/` path

## Diagram Requirements

Please create a comprehensive architecture diagram showing:

1. **Layered Architecture**: Frontend → API → Agents → Database
2. **Data Flow**: Show arrows indicating request/response flow
3. **Agent Interactions**: How the 3 agents communicate and share data
4. **Database Connections**: Which components access which tables
5. **External Dependencies**: AI models, libraries
6. **Security Boundaries**: Where authentication/validation occurs
7. **Caching Layer**: How caching improves performance

**Style Preferences**:
- Use different colors for different layers (Frontend, API, Agents, Database)
- Show the multi-agent workflow clearly
- Indicate synchronous vs asynchronous operations
- Include technology labels (FastAPI, SQLite, FLAN-T5, etc.)
- Show the prediction generation flow as the main path
- Use standard architecture diagram notation (boxes, arrows, cylinders for DB)

**Format**: Generate as a Mermaid diagram, PlantUML, or any standard architecture diagram format.
