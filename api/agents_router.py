"""
API Router for Agentic Medical Diagnosis System

Provides endpoints for:
- /agents/predict: Generate predictions using agent workflow
- /agents/refine: Refine DAG with clinician feedback
- /agents/dag/{patient_id}: Get latest DAG for patient
- /agents/upload_doc: Upload and process medical documents
- /chat: Interactive chat with medical AI
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import json
from datetime import datetime
import pdfplumber
import io

from agents import KnowledgeSynthesisAgent, CausalDiscoveryAgent, DecisionMakingAgent
from agents.ollama_adapter import OllamaAdapter
from database.db_utils import get_db_connection, transaction
from api.security import get_current_username, check_rate_limit, validate_file_upload
from api.models import (
    PredictRequest, RefineRequest, ChatRequest, UploadDocRequest,
    PredictionResponse, ChatResponse, UploadResponse
)

router = APIRouter(tags=["agents"])

# Database path
DB_PATH = "database/medical_knowledge.db"

# Initialize agents (module-level singletons)
knowledge_agent = None
causal_agent = None
decision_agent = None
ollama_adapter = None


def get_agents():
    """Get or initialize agent instances (singleton pattern)."""
    global knowledge_agent, causal_agent, decision_agent, ollama_adapter
    
    if knowledge_agent is None:
        knowledge_agent = KnowledgeSynthesisAgent(db_path=DB_PATH)
    if causal_agent is None:
        causal_agent = CausalDiscoveryAgent(db_path=DB_PATH)
    if decision_agent is None:
        decision_agent = DecisionMakingAgent()
    if ollama_adapter is None:
        try:
            ollama_adapter = OllamaAdapter(model_name="llama3.2")
            ollama_adapter.test_ollama()
            print("✓ Ollama adapter initialized successfully")
        except Exception as e:
            print(f"⚠ Ollama not available: {e}")
            ollama_adapter = None
    
    return knowledge_agent, causal_agent, decision_agent


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    """
    Generate disease predictions using full agent workflow.
    
    PRODUCTION FEATURES:
    - ✅ HTTP Basic Auth required
    - ✅ Rate limiting (100 req/min per IP)
    - ✅ Transaction safety with auto-rollback
    - ✅ Agent memory persistence (load/save DAG)
    - ✅ Knowledge summary cache
    - ✅ Pydantic validation
    
    Workflow:
    1. Fetch patient history
    2. Load existing DAG from agent_memories (if exists)
    3. Build candidate set (CausalDiscoveryAgent)
    4. Check knowledge summary cache, retrieve if needed
    5. Generate/refine DAG (CausalDiscoveryAgent)
    6. Rank and explain (DecisionMakingAgent)
    7. Store prediction and DAG in database (transactional)
    
    Returns:
        Prediction results with explanations and evidence
    """
    try:
        # Rate limiting
        check_rate_limit(fastapi_request)
        
        # Get agents
        knowledge_agent, causal_agent, decision_agent = get_agents()
        
        with get_db_connection(DB_PATH) as conn:
            # Step 1: Get patient history (read-only, no transaction needed)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.visit_id, v.visit_date, d.disease_code, d.disease_name
                FROM visits v
                JOIN diagnoses d ON v.visit_id = d.visit_id
                WHERE v.patient_id = ?
                ORDER BY v.visit_date
            """, (request.patient_id,))
            
            history_rows = cursor.fetchall()
            
            if not history_rows:
                raise HTTPException(status_code=404, detail="Patient history not found")
            
            # Get last visit
            last_visit_id = history_rows[-1][0]
            diagnosis_history = [row[2] for row in history_rows]
            current_diseases = list(set([row[2] for row in history_rows if row[0] == last_visit_id]))
            
            # Step 2: Load existing DAG from agent_memories
            cursor.execute("""
                SELECT dag_json
                FROM agent_memories
                WHERE patient_id = ?
                ORDER BY last_updated DESC
                LIMIT 1
            """, (request.patient_id,))
            
            existing_dag_row = cursor.fetchone()
            existing_dag = json.loads(existing_dag_row[0]) if existing_dag_row else None
            
            # Step 3: Build candidate set
            candidates = causal_agent.build_candidate_set(
                request.patient_id,
                last_visit_id,
                epsilon=0.01
            )
            
            # Fallback if no candidates
            if not candidates:
                fallback_map = {
                    "I21.9": [("I50.9", 0.5), ("I25.2", 0.3)],
                    "I25.10": [("I21.9", 0.4), ("I50.9", 0.3)],
                    "N18.4": [("I50.9", 0.4), ("D63.1", 0.3), ("N18.5", 0.5)],
                    "N18.3": [("N18.4", 0.5), ("I50.9", 0.3)],
                    "I10": [("N18.3", 0.3), ("I25.10", 0.3), ("I63.9", 0.2)],
                    "E11": [("N18.3", 0.4), ("I25.10", 0.3), ("G63.2", 0.2)],
                }
            
            # Build candidate set
            candidates_list = causal_agent.build_candidate_set(request.patient_id, last_visit_id)
            
            # Fallback if no candidates from transition matrix
            if not candidates_list:
                # Use common progressions based on current diseases
                candidates_list = []
                for disease in current_diseases:
                    if disease in ["I21.9", "I50.9"]:
                        candidates_list.extend(["I50.9", "I25.2", "I11.0"])
                    elif disease in ["N18.3", "N18.4"]:
                        candidates_list.extend(["N18.5", "I50.9", "D63.1"])
                    elif disease == "E11":
                        candidates_list.extend(["N18.3", "I25.10", "G63.2"])
                
                # Remove duplicates and limit
                candidates_list = list(dict.fromkeys(candidates_list))[:10]
                
                # If still empty, use defaults
                if not candidates_list:
                    candidates_list = ["I50.9", "N18.5", "I25.2", "D63.1"]
            
            # Step 4: Get knowledge summaries (check cache first)
            cached_summaries = []
            if not request.clinician_comment:
                # Check cache
                cursor.execute("""
                    SELECT doc_id, summary, similarity
                    FROM knowledge_summary_cache
                    WHERE patient_id = ? AND visit_id = ?
                    ORDER BY similarity DESC
                    LIMIT 10
                """, (request.patient_id, last_visit_id))
                
                cached_summaries = [
                    {
                        "doc_id": row[0],
                        "disease_code": "General Medical Knowledge",
                        "snippet": row[1],
                        "summary": row[1],
                        "similarity": row[2]
                    }
                    for row in cursor.fetchall()
                ]
            
            # Generate summaries if not cached
            if cached_summaries:
                summaries = cached_summaries
            else:
                # Generate query and retrieve knowledge
                query = knowledge_agent.generate_query(diagnosis_history, candidates_list[:10])
                summaries = knowledge_agent.retrieve_and_summarize(query, top_k=10)
            
            # Step 5: Generate/refine DAG
            # Generate or load DAG
            if existing_dag:
                dag = existing_dag
            else:
                dag = causal_agent.generate_initial_dag(candidates_list[:10])  # Top 10 candidates
                
            # Fit DAG with data
            dag = causal_agent.fit_graph_with_data(dag)
            
            # Convert candidates to tuples (disease_code, score) for decision agent
            # Get scores from DAG edges or use default
            candidates_with_scores = []
            for edge in dag.get("edges", []):
                candidates_with_scores.append((edge["to"], edge.get("weight", 0.5)))
            
            # If no edges, use nodes with default score
            if not candidates_with_scores:
                for node in dag.get("nodes", []):
                    candidates_with_scores.append((node["id"], 0.5))
            
            # Step 6: Rank and explain
            patient_summary = f"Patient with history of {', '.join(diagnosis_history[-3:])}"
            result = decision_agent.rank_and_explain(
                patient_summary=patient_summary,
                candidates=candidates_with_scores,
                dag=dag,
                summaries=summaries,
                clinician_comment=request.clinician_comment or ""
            )
            
            # Step 7: Store prediction with transaction safety
            with transaction(conn):
                # Store prediction
                cursor.execute("""
                    INSERT INTO predictions (
                        patient_id, visit_id, predicted_disease_code, explanation, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    request.patient_id,
                    last_visit_id,
                    result["predictions"][0]["code"] if result["predictions"] else "UNKNOWN",
                    result["explanation"],
                    datetime.now().isoformat()
                ))
                
                prediction_id = cursor.lastrowid
                
                # Store/update DAG in agent_memories
                cursor.execute("""
                    INSERT OR REPLACE INTO agent_memories (
                        patient_id, dag_json, edit_action, edit_reason, last_updated
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    request.patient_id,
                    json.dumps(dag),
                    "predict",
                    f"Prediction {prediction_id}",
                    datetime.now().isoformat()
                ))
                
                # Store summaries in cache if not cached
                if not cached_summaries:
                    for summary in summaries:
                        cursor.execute("""
                            INSERT OR IGNORE INTO knowledge_summary_cache (
                                patient_id, visit_id, doc_id, summary, similarity, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            request.patient_id,
                            last_visit_id,
                            summary.get("doc_id", 0),
                            summary.get("summary", ""),
                            summary.get("similarity", 0.0),
                            datetime.now().isoformat()
                        ))
            
            # Add prediction_id to result
            result["prediction_id"] = prediction_id
            
            return PredictionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/refine", response_model=PredictionResponse)
async def refine(
    request: RefineRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    """
    Refine DAG with clinician feedback.
    
    PRODUCTION FEATURES:
    - ✅ HTTP Basic Auth required
    - ✅ Rate limiting (100 req/min per IP)
    - ✅ Transaction safety with auto-rollback
    - ✅ Agent memory persistence
    - ✅ Pydantic validation
    
    Args:
        request: Contains patient_id and feedback dict with action, from, to, reason
        
    Returns:
        Updated DAG and predictions
    """
    try:
        # Rate limiting
        check_rate_limit(fastapi_request)
        
        # Get agents
        knowledge_agent, causal_agent, decision_agent = get_agents()
        
        feedback = request.feedback
        action = feedback.get("action")
        from_disease = feedback.get("from")
        to_disease = feedback.get("to")
        reason = feedback.get("reason", "")
        
        with get_db_connection(DB_PATH) as conn:
            # Load latest DAG from agent_memories
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dag_json
                FROM agent_memories
                WHERE patient_id = ?
                ORDER BY last_updated DESC
                LIMIT 1
            """, (request.patient_id,))
            
            dag_row = cursor.fetchone()
            
            if dag_row:
                dag = json.loads(dag_row[0])
            else:
                # No existing DAG, create minimal one
                dag = {"nodes": [], "edges": []}
            
            # Apply clinician edit
            dag = causal_agent.apply_clinician_edit(
                dag, action, from_disease, to_disease, reason
            )
            
            # Get patient history for re-ranking
            cursor.execute("""
                SELECT v.visit_id, d.disease_code
                FROM visits v
                JOIN diagnoses d ON v.visit_id = d.visit_id
                WHERE v.patient_id = ?
                ORDER BY v.visit_date
            """, (request.patient_id,))
            
            history_rows = cursor.fetchall()
            last_visit_id = history_rows[-1][0] if history_rows else None
            diagnosis_history = [row[1] for row in history_rows]
            
            # Step 4: Get knowledge summaries (check cache first)
            cached_summaries = []
            if not request.clinician_comment:
                # Check cache
                cursor.execute("""
                    SELECT doc_id, summary, similarity
                    FROM knowledge_summary_cache
                    WHERE patient_id = ? AND visit_id = ?
                    ORDER BY similarity DESC
                    LIMIT 10
                """, (request.patient_id, last_visit_id))
                
                cached_summaries = [
                    {
                        "doc_id": row[0],
                        "disease_code": "General Medical Knowledge",  # More descriptive than "CACHED"
                        "snippet": row[1],
                        "summary": row[1],
                        "similarity": row[2]
                    }
                    for row in cursor.fetchall()
                ]
            
            # Generate summaries if not cached
            if cached_summaries:
                summaries = cached_summaries
            else:
                # Build candidates list - it's already a list of disease codes (strings)
                # Extract candidates from DAG
                candidates = [edge["to"] for edge in dag.get("edges", [])]
                if not candidates:
                    candidates = [from_disease, to_disease] # Fallback if DAG is empty
                
                candidates_list = candidates if isinstance(candidates, list) else [candidates]
                query = knowledge_agent.generate_query(diagnosis_history, candidates_list)
                summaries = knowledge_agent.retrieve_and_summarize(query, top_k=10)
            
            # Re-rank with updated DAG
            patient_summary = f"Patient with history of {', '.join(diagnosis_history[-3:])}"
            
            # Convert candidates to tuples format (disease_code, score) for decision agent
            candidate_tuples = []
            for edge in dag.get("edges", []):
                candidate_tuples.append((edge["to"], edge.get("weight", 0.5)))
            
            # If no edges, use the diseases from the feedback
            if not candidate_tuples:
                candidate_tuples = [(from_disease, 0.5), (to_disease, 0.5)]
            
            result = decision_agent.rank_and_explain(
                patient_summary=patient_summary,
                candidates=candidate_tuples,
                dag=dag,
                summaries=summaries,
                clinician_comment=reason
            )
            
            # Store updated DAG and prediction (TRANSACTIONAL)
            with transaction(conn) as cursor:
                # Store updated DAG in agent_memories
                cursor.execute("""
                    INSERT INTO agent_memories (
                        patient_id, dag_json, edit_action, edit_reason, last_updated
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    request.patient_id,
                    json.dumps(dag),
                    action,
                    reason,
                    datetime.now().isoformat()
                ))
                
                # Store new prediction
                if last_visit_id:
                    cursor.execute("""
                        INSERT INTO predictions (
                            patient_id, visit_id, predicted_disease_code, explanation, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        request.patient_id,
                        last_visit_id,
                        result["predictions"][0]["code"] if result["predictions"] else "UNKNOWN",
                        result["explanation"],
                        datetime.now().isoformat()
                    ))
            
            return PredictionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")


@router.get("/dag/{patient_id}")
async def get_dag(patient_id: int):
    """
    Get latest DAG for patient.
    
    Args:
        patient_id: Patient ID
        
    Returns:
        Latest DAG from predictions or agent_memories
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Try agent_memories first (most recent edits)
        cursor.execute("""
            SELECT dag_json
            FROM agent_memories
            WHERE patient_id = ?
            ORDER BY last_updated DESC
            LIMIT 1
        """, (patient_id,))
        
        result = cursor.fetchone()
        
        if result:
            dag = json.loads(result[0])
        else:
            # Try predictions
            cursor.execute("""
                SELECT explanation
                FROM predictions
                WHERE patient_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (patient_id,))
            
            result = cursor.fetchone()
            
            if result:
                prediction_data = json.loads(result[0])
                dag = prediction_data.get("dag", {"nodes": [], "edges": []})
            else:
                dag = {"nodes": [], "edges": []}
        
        conn.close()
        
        return {
            "patient_id": patient_id,
            "dag": dag
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve DAG: {str(e)}")


@router.post("/upload_doc", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    disease_code: Optional[str] = Form(None),
    fastapi_request: Request = None,
    username: str = Depends(get_current_username)
):
    """
    Upload and process medical document.
    
    PRODUCTION FEATURES:
    - ✅ HTTP Basic Auth required
    - ✅ Rate limiting (100 req/min per IP)
    - ✅ File validation (5MB max, .pdf/.txt only)
    - ✅ Transaction safety with auto-rollback
    - ✅ Pydantic validation
    
    Supports PDF and plaintext files. Extracts text, chunks it, generates embeddings,
    and stores in knowledge_documents and document_embeddings.
    
    Args:
        file: Uploaded file (PDF or text)
        disease_code: Optional disease code to associate with document
        
    Returns:
        Created document IDs and preview snippets
    """
    try:
        # Rate limiting
        check_rate_limit(fastapi_request)
        
        # Read file content
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        # Validate file upload
        safe_filename = validate_file_upload(
            filename=file.filename,
            file_size=file_size,
            max_size_mb=5,
            allowed_extensions={'.pdf', '.txt'}
        )
        
        # Extract text based on file type
        if file.filename.endswith('.pdf'):
            # Parse PDF
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse PDF: {str(e)}"
                )
        else:
            # Assume plaintext
            text = file_bytes.decode('utf-8', errors='ignore')
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text extracted from file")
        
        # Chunk text into ~500-800 token segments
        chunks = _chunk_text(text, max_words=600)
        
        # Initialize knowledge agent for embeddings
        knowledge_agent, _, _ = get_agents()
        
        doc_ids = []
        preview_snippets = []
        
        with get_db_connection(DB_PATH) as conn:
            # Store all chunks in transaction
            with transaction(conn) as cursor:
                for i, chunk in enumerate(chunks):
                    # Insert into knowledge_documents
                    cursor.execute("""
                        INSERT INTO knowledge_documents
                        (disease_code, section, content)
                        VALUES (?, ?, ?)
                    """, (disease_code or "UPLOADED", f"uploaded_chunk_{i+1}", chunk))
                    
                    doc_id = cursor.lastrowid
                    doc_ids.append(doc_id)
                    
                    # Generate embedding
                    embedding = knowledge_agent.model.encode(chunk, convert_to_numpy=True)
                    
                    # Store embedding
                    cursor.execute("""
                        INSERT INTO document_embeddings
                        (doc_id, embedding)
                        VALUES (?, ?)
                    """, (doc_id, json.dumps(embedding.tolist())))
                    
                    # Create preview snippet
                    preview = chunk[:200] + ("..." if len(chunk) > 200 else "")
                    preview_snippets.append({
                        "doc_id": doc_id,
                        "preview": preview
                    })
        
        return UploadResponse(
            message=f"Successfully uploaded and processed {len(chunks)} chunks",
            doc_ids=doc_ids,
            preview_snippets=preview_snippets,
            filename=safe_filename,
            disease_code=disease_code
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


        
        return {
            "message": f"Document uploaded successfully. Created {len(doc_ids)} chunks.",
            "doc_ids": doc_ids,
            "preview_snippets": preview_snippets,
            "filename": file.filename,
            "disease_code": disease_code
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


def _chunk_text(text: str, max_words: int = 600) -> List[str]:
    """
    Chunk text into segments of approximately max_words.
    
    Args:
        text: Input text
        max_words: Maximum words per chunk
        
    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i+max_words])
        chunks.append(chunk)
    
    return chunks


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    """
    Interactive chat with medical AI.
    
    PRODUCTION FEATURES:
    - ✅ HTTP Basic Auth required
    - ✅ Rate limiting (100 req/min per IP)
    - ✅ Transaction safety with auto-rollback
    - ✅ Pydantic validation
    
    Stores conversation history and uses Ollama/DecisionMakingAgent to generate responses.
    
    Args:
        request: Contains patient_id and message
        
    Returns:
        Assistant reply and conversation_id
    """
    try:
        # Rate limiting
        check_rate_limit(fastapi_request)
        
        # Get agents
        knowledge_agent, causal_agent, decision_agent = get_agents()
        
        with get_db_connection(DB_PATH) as conn:
            # Get patient context
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.disease_code
                FROM diagnoses d
                JOIN visits v ON d.visit_id = v.visit_id
                WHERE v.patient_id = ?
                ORDER BY v.visit_date DESC
                LIMIT 5
            """, (request.patient_id,))
            
            recent_diagnoses = [row[0] for row in cursor.fetchall()]
            
            # Get conversation history
            cursor.execute("""
                SELECT role, message
                FROM conversations
                WHERE patient_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (request.patient_id,))
            
            history = [(row[0], row[1]) for row in cursor.fetchall()]
            history.reverse()
            
            # Get knowledge summaries
            summaries = []
            if recent_diagnoses:
                query = knowledge_agent.generate_query(recent_diagnoses, [])
                summaries = knowledge_agent.retrieve_and_summarize(query, top_k=5)
            
            # Build chat prompt
            context = f"Patient {request.patient_id} with recent diagnoses: {', '.join(recent_diagnoses)}"
            knowledge_context = ""
            if summaries:
                knowledge_context = "\n\nRelevant medical knowledge:\n" + "\n".join([
                    f"- {s.get('disease_code', 'N/A')}: {s.get('summary', '')[:150]}"
                    for s in summaries[:3]
                ])
            
            history_str = "\n".join([f"{role.capitalize()}: {msg}" for role, msg in history[-5:]])
            
            chat_prompt = f"""You are a helpful medical AI assistant.

Patient Context: {context}
{knowledge_context}

Conversation History:
{history_str}

Patient: {request.message}

Respond concisely and helpfully."""
            
            # Generate response
            global ollama_adapter
            try:
                if ollama_adapter is not None and ollama_adapter.enabled:
                    reply = ollama_adapter.generate(chat_prompt, max_tokens=300).strip()
                else:
                    reply = decision_agent._generate_from_model(chat_prompt, max_length=200)
            except Exception:
                reply = f"I understand you're asking about {request.message}. Based on the patient's history, I recommend consulting with a healthcare provider."
            
            # Store conversation (TRANSACTIONAL)
            with transaction(conn) as cursor:
                # Store user message
                cursor.execute("""
                    INSERT INTO conversations
                    (patient_id, role, message, created_at)
                    VALUES (?, 'user', ?, ?)
                """, (request.patient_id, request.message, datetime.now().isoformat()))
                
                conversation_id = cursor.lastrowid
                
                # Store assistant reply
                cursor.execute("""
                    INSERT INTO conversations
                    (patient_id, role, message, created_at)
                    VALUES (?, 'assistant', ?, ?)
                """, (request.patient_id, reply, datetime.now().isoformat()))
            
            return ChatResponse(
                reply=reply,
                conversation_id=conversation_id,
                patient_id=request.patient_id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
