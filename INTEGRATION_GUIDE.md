# Production Enhancements - Integration Guide

## 🎯 Quick Status

**Completed**: 40% (Infrastructure ready)  
**Remaining**: 60% (Integration needed)  
**Estimated Time**: 8-12 hours

---

## ✅ What's Ready to Use

All infrastructure is built and tested:

1. **Model Pool** (`agents/model_pool.py`) - ✅ Working
2. **Database Utils** (`database/db_utils.py`) - ✅ Ready
3. **Security Module** (`api/security.py`) - ✅ Ready
4. **Pydantic Models** (`api/models.py`) - ✅ Ready
5. **Enhanced JSON Parsing** - ✅ Working
6. **Startup Script** (`start.sh`) - ✅ Working

---

## 🔧 Integration Steps

### Step 1: Update /predict Endpoint (2 hours)

**File**: `api/agents_router.py`

**Current Code** (line ~64):
```python
@router.post("/predict")
async def predict(request: PredictRequest):
```

**Replace With**:
```python
@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    # Add rate limiting
    check_rate_limit(fastapi_request)
    
    # ... existing code ...
    
    # Replace all conn = sqlite3.connect() with:
    with get_db_connection(DB_PATH) as conn:
        # Read operations (no transaction needed)
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        
        # ... processing ...
        
        # Write operations (use transaction)
        with transaction(conn) as cursor:
            cursor.execute("INSERT INTO predictions ...")
            cursor.execute("INSERT INTO agent_memories ...")
```

**Full Enhanced Version**: See `api/enhanced_predict_endpoint.py`

---

### Step 2: Update /refine Endpoint (1 hour)

**Add**:
```python
@router.post("/refine", response_model=PredictionResponse)
async def refine(
    request: RefineRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    check_rate_limit(fastapi_request)
    
    with get_db_connection(DB_PATH) as conn:
        # Load DAG from agent_memories
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dag_json FROM agent_memories
            WHERE patient_id = ?
            ORDER BY last_updated DESC LIMIT 1
        """, (request.patient_id,))
        
        dag_row = cursor.fetchone()
        if not dag_row:
            raise HTTPException(404, "No DAG found for patient")
        
        dag = json.loads(dag_row[0])
        
        # Apply clinician edit
        updated_dag = causal_agent.apply_clinician_edit(
            dag=dag,
            action=request.feedback["action"],
            from_disease=request.feedback["from"],
            to_disease=request.feedback["to"],
            reason=request.feedback["reason"]
        )
        
        # Recalculate predictions with updated DAG
        # ... (similar to predict endpoint) ...
        
        # Save updated DAG
        with transaction(conn) as cursor:
            cursor.execute("""
                INSERT INTO agent_memories (
                    patient_id, dag_json, edit_action, edit_reason, last_updated
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                request.patient_id,
                json.dumps(updated_dag),
                request.feedback["action"],
                request.feedback["reason"],
                datetime.now().isoformat()
            ))
```

---

### Step 3: Update /upload_doc Endpoint (1 hour)

**Add**:
```python
@router.post("/upload_doc", response_model=UploadResponse)
async def upload_doc(
    file: UploadFile = File(...),
    disease_code: Optional[str] = Form(None),
    fastapi_request: Request = None,
    username: str = Depends(get_current_username)
):
    check_rate_limit(fastapi_request)
    
    # Read file
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validate upload
    safe_filename = validate_file_upload(
        filename=file.filename,
        file_size=file_size,
        max_size_mb=5,
        allowed_extensions={'.pdf', '.txt'}
    )
    
    # ... rest of upload logic ...
    
    # Use transaction for database writes
    with get_db_connection(DB_PATH) as conn:
        with transaction(conn) as cursor:
            for chunk in chunks:
                cursor.execute("""
                    INSERT INTO knowledge_documents (...)
                    VALUES (...)
                """, (...))
                
                cursor.execute("""
                    INSERT INTO document_embeddings (...)
                    VALUES (...)
                """, (...))
```

---

### Step 4: Update /chat Endpoint (30 min)

**Add**:
```python
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    fastapi_request: Request,
    username: str = Depends(get_current_username)
):
    check_rate_limit(fastapi_request)
    
    # ... existing chat logic ...
    
    # Use transaction for storing conversation
    with get_db_connection(DB_PATH) as conn:
        with transaction(conn) as cursor:
            cursor.execute("""
                INSERT INTO conversations (...)
                VALUES (...)
            """, (...))
```

---

### Step 5: Add Global Exception Handler (15 min)

**File**: `app.py`

**Add after app initialization**:
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled errors."""
    import traceback
    
    # Log the error
    print(f"ERROR: {exc}")
    traceback.print_exc()
    
    # Return JSON error response
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": str(request.url)
        }
    )
```

---

### Step 6: Update Knowledge Summary Cache (1 hour)

**File**: `agents/knowledge_synthesis.py`

**Add method**:
```python
def retrieve_and_summarize_with_cache(
    self,
    patient_id: int,
    visit_id: int,
    query: str,
    top_k: int = 10
) -> List[Dict]:
    """
    Retrieve and summarize with caching.
    
    Checks cache first, retrieves if not cached.
    """
    # Check cache
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doc_id, summary, similarity
        FROM knowledge_summary_cache
        WHERE patient_id = ? AND visit_id = ?
    """, (patient_id, visit_id))
    
    cached = cursor.fetchall()
    
    if cached:
        conn.close()
        return [
            {
                "doc_id": row[0],
                "summary": row[1],
                "similarity": row[2]
            }
            for row in cached
        ]
    
    # Not cached, retrieve normally
    summaries = self.retrieve_and_summarize(query, top_k)
    
    # Store in cache
    for summary in summaries:
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_summary_cache (
                patient_id, visit_id, doc_id, summary, similarity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            visit_id,
            summary["doc_id"],
            summary["summary"],
            summary["similarity"],
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    return summaries
```

---

## 📋 Checklist

### Critical Path
- [ ] Update /predict with auth, rate limiting, transactions, agent memory, cache
- [ ] Update /refine with auth, rate limiting, transactions, agent memory
- [ ] Update /upload_doc with auth, rate limiting, transactions, file validation
- [ ] Update /chat with auth, rate limiting, transactions
- [ ] Add global exception handler to app.py
- [ ] Add cache method to KnowledgeSynthesisAgent
- [ ] Test all endpoints
- [ ] Verify auth works
- [ ] Verify rate limiting works
- [ ] Verify transactions rollback on error

### Optional
- [ ] UI/UX enhancements (glassmorphism, responsive, etc.)
- [ ] Streaming chat endpoint
- [ ] Docker deployment
- [ ] Additional tests

---

## 🧪 Testing After Integration

### 1. Test Auth
```bash
# Should fail (no auth)
curl -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'

# Should succeed
curl -X POST http://localhost:8001/agents/predict \
  -u admin:changeme123 \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'
```

### 2. Test Rate Limiting
```bash
# Run 101 requests quickly
for i in {1..101}; do
  curl -u admin:changeme123 \
    -X POST http://localhost:8001/agents/predict \
    -H "Content-Type: application/json" \
    -d '{"patient_id": 1}'
done
# Should get 429 error on 101st request
```

### 3. Test Transactions
```python
# In Python, test rollback
import sqlite3

# Cause an error mid-transaction
# Verify database not corrupted
```

### 4. Test Agent Memory
```bash
# First prediction
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -d '{"patient_id": 1}'

# Check agent_memories table
sqlite3 database/medical_knowledge.db \
  "SELECT * FROM agent_memories WHERE patient_id = 1"

# Should see DAG stored
```

### 5. Test Cache
```bash
# First request (slow, no cache)
time curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -d '{"patient_id": 1}'

# Second request (fast, cached)
time curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -d '{"patient_id": 1}'

# Should be ~70% faster
```

---

## 🚨 Common Issues

### Issue: Import errors after changes
**Solution**:
```bash
# Restart server
# Kill existing server (Ctrl+C)
./start.sh
```

### Issue: Auth not working
**Solution**:
```bash
# Check environment variables
echo $AUTH_USERNAME
echo $AUTH_PASSWORD

# Set if needed
export AUTH_USERNAME=admin
export AUTH_PASSWORD=changeme123
```

### Issue: Database locked
**Solution**:
```bash
# Check for open connections
lsof database/medical_knowledge.db

# Kill if needed
kill -9 <PID>
```

### Issue: Models not loading
**Solution**:
```bash
# Check startup logs
# Should see:
# 📦 Loading embedding model...
# ✅ Embedding model loaded
# 📦 Loading SLM model...
# ✅ SLM model loaded
```

---

## 📊 Expected Performance

### Before Integration
- First prediction: 3-5 seconds
- Subsequent: <1 second
- No auth, no rate limiting
- No caching

### After Integration
- Server startup: 10-15 seconds (one-time)
- First prediction: 1-2 seconds (70% faster!)
- Cached prediction: <0.5 seconds (70% faster!)
- Auth protected
- Rate limited (100/min)
- Transaction safe

---

## 🎯 Priority Order

1. **HIGHEST**: /predict endpoint (most used, most complex)
2. **HIGH**: Global exception handler (safety)
3. **HIGH**: /refine endpoint (clinician workflow)
4. **MEDIUM**: /upload_doc endpoint (less frequent)
5. **MEDIUM**: /chat endpoint (less critical)
6. **LOW**: Cache method (optimization)
7. **OPTIONAL**: UI/UX enhancements

---

## 💡 Tips

1. **Test incrementally**: Add one feature at a time, test, then add next
2. **Use enhanced_predict_endpoint.py as reference**: It has all features integrated
3. **Check logs**: Print statements help debug
4. **Use transactions**: Wrap all writes in `with transaction(conn)`
5. **Validate inputs**: Pydantic models catch bad data early
6. **Handle errors**: Try/except with HTTPException

---

## 📝 Summary

**Infrastructure**: ✅ 100% Complete  
**Integration**: ❌ 0% Complete  
**Estimated Time**: 8-12 hours

**Next Action**: Start with /predict endpoint using enhanced_predict_endpoint.py as template

**Files to Modify**:
1. `api/agents_router.py` - All endpoints
2. `app.py` - Exception handler
3. `agents/knowledge_synthesis.py` - Cache method

**Files Already Created**:
- `agents/model_pool.py` ✅
- `database/db_utils.py` ✅
- `api/security.py` ✅
- `api/models.py` ✅
- `api/enhanced_predict_endpoint.py` ✅ (reference implementation)
- `start.sh` ✅

**Ready to integrate!** 🚀
