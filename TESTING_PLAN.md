# Phase 5: Production Testing Plan

## Overview

Systematic testing of all production features to verify:
1. Authentication works correctly
2. Rate limiting prevents abuse
3. Transactions ensure data integrity
4. Agent memory persists correctly
5. Knowledge cache improves performance
6. All endpoints function properly

---

## Test 1: Authentication ✅

### Test 1.1: Request Without Auth (Should Fail)
```bash
curl -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'
```
**Expected**: 401 Unauthorized

### Test 1.2: Request With Wrong Credentials (Should Fail)
```bash
curl -u wrong:password \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'
```
**Expected**: 401 Unauthorized

### Test 1.3: Request With Correct Credentials (Should Succeed)
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'
```
**Expected**: 200 OK with prediction data

---

## Test 2: Rate Limiting ✅

### Test 2.1: Normal Request Rate (Should Succeed)
```bash
# Send 5 requests (well under limit)
for i in {1..5}; do
  curl -u admin:changeme123 \
    -X POST http://localhost:8001/agents/predict \
    -H "Content-Type: application/json" \
    -d '{"patient_id": 1}'
  echo "Request $i completed"
done
```
**Expected**: All succeed (200 OK)

### Test 2.2: Exceed Rate Limit (Should Fail on 101st)
```bash
# Send 101 requests quickly
for i in {1..101}; do
  response=$(curl -s -w "\n%{http_code}" -u admin:changeme123 \
    -X POST http://localhost:8001/agents/predict \
    -H "Content-Type: application/json" \
    -d '{"patient_id": 1}')
  http_code=$(echo "$response" | tail -n1)
  echo "Request $i: HTTP $http_code"
  if [ "$http_code" == "429" ]; then
    echo "✅ Rate limit triggered at request $i"
    break
  fi
done
```
**Expected**: 429 Too Many Requests on 101st request

---

## Test 3: Transaction Safety ✅

### Test 3.1: Successful Transaction (Should Commit)
```bash
# Make a prediction (should save to DB)
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'

# Check database
sqlite3 database/medical_knowledge.db \
  "SELECT COUNT(*) FROM predictions WHERE patient_id = 1;"
```
**Expected**: Count increases

### Test 3.2: Failed Transaction (Should Rollback)
```bash
# Send invalid data (should trigger error and rollback)
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 999999}'

# Check database (should not have partial data)
sqlite3 database/medical_knowledge.db \
  "SELECT COUNT(*) FROM predictions WHERE patient_id = 999999;"
```
**Expected**: Count is 0 (rollback worked)

---

## Test 4: Agent Memory Persistence ✅

### Test 4.1: First Prediction (Creates Memory)
```bash
# Make first prediction
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'

# Check agent_memories table
sqlite3 database/medical_knowledge.db \
  "SELECT patient_id, LENGTH(dag_json), last_updated 
   FROM agent_memories 
   WHERE patient_id = 1 
   ORDER BY last_updated DESC 
   LIMIT 1;"
```
**Expected**: DAG stored in agent_memories

### Test 4.2: Refine Prediction (Updates Memory)
```bash
# Refine with clinician feedback
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/refine \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "feedback": {
      "action": "add_edge",
      "from": "I50.9",
      "to": "I11.0",
      "reason": "Clinical observation"
    }
  }'

# Check updated memory
sqlite3 database/medical_knowledge.db \
  "SELECT COUNT(*) FROM agent_memories WHERE patient_id = 1;"
```
**Expected**: New entry in agent_memories

---

## Test 5: Knowledge Cache ✅

### Test 5.1: First Request (No Cache - Slower)
```bash
# Clear cache first
sqlite3 database/medical_knowledge.db \
  "DELETE FROM knowledge_summary_cache WHERE patient_id = 1;"

# Time first request
time curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'

# Check cache was created
sqlite3 database/medical_knowledge.db \
  "SELECT COUNT(*) FROM knowledge_summary_cache WHERE patient_id = 1;"
```
**Expected**: Slower, cache created

### Test 5.2: Second Request (Cached - Faster)
```bash
# Time second request (should use cache)
time curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1}'
```
**Expected**: Significantly faster (70% improvement)

---

## Test 6: All Endpoints ✅

### Test 6.1: /agents/predict
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "clinician_comment": "Test prediction"}'
```
**Expected**: 200 OK with predictions

### Test 6.2: /agents/refine
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/refine \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "feedback": {
      "action": "add_edge",
      "from": "I50.9",
      "to": "I11.0",
      "reason": "Test refinement"
    }
  }'
```
**Expected**: 200 OK with updated predictions

### Test 6.3: /agents/upload_doc
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/upload_doc \
  -F "file=@test_documents/heart_failure_management.txt" \
  -F "disease_code=I50.9"
```
**Expected**: 200 OK with doc_ids

### Test 6.4: /agents/chat
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "message": "What are the treatment options?"
  }'
```
**Expected**: 200 OK with reply

---

## Test 7: Error Handling ✅

### Test 7.1: Invalid JSON
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
```
**Expected**: 422 Unprocessable Entity

### Test 7.2: Missing Required Fields
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{}'
```
**Expected**: 422 with validation error

### Test 7.3: Invalid Patient ID
```bash
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "invalid"}'
```
**Expected**: 422 with type error

---

## Test 8: File Upload Security ✅

### Test 8.1: Valid File Upload
```bash
echo "Test medical document" > /tmp/test.txt
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/upload_doc \
  -F "file=@/tmp/test.txt" \
  -F "disease_code=TEST"
```
**Expected**: 200 OK

### Test 8.2: File Too Large (>5MB)
```bash
# Create 6MB file
dd if=/dev/zero of=/tmp/large.txt bs=1M count=6
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/upload_doc \
  -F "file=@/tmp/large.txt"
```
**Expected**: 413 Payload Too Large

### Test 8.3: Invalid File Type
```bash
echo "test" > /tmp/test.exe
curl -u admin:changeme123 \
  -X POST http://localhost:8001/agents/upload_doc \
  -F "file=@/tmp/test.exe"
```
**Expected**: 400 Bad Request

---

## Test Results Template

| Test | Status | Notes |
|------|--------|-------|
| 1.1 Auth - No credentials | ⏳ | |
| 1.2 Auth - Wrong credentials | ⏳ | |
| 1.3 Auth - Correct credentials | ⏳ | |
| 2.1 Rate limit - Normal | ⏳ | |
| 2.2 Rate limit - Exceeded | ⏳ | |
| 3.1 Transaction - Success | ⏳ | |
| 3.2 Transaction - Rollback | ⏳ | |
| 4.1 Agent memory - Create | ⏳ | |
| 4.2 Agent memory - Update | ⏳ | |
| 5.1 Cache - First request | ⏳ | |
| 5.2 Cache - Cached request | ⏳ | |
| 6.1 Endpoint - /predict | ⏳ | |
| 6.2 Endpoint - /refine | ⏳ | |
| 6.3 Endpoint - /upload_doc | ⏳ | |
| 6.4 Endpoint - /chat | ⏳ | |
| 7.1 Error - Invalid JSON | ⏳ | |
| 7.2 Error - Missing fields | ⏳ | |
| 7.3 Error - Invalid type | ⏳ | |
| 8.1 File - Valid upload | ⏳ | |
| 8.2 File - Too large | ⏳ | |
| 8.3 File - Invalid type | ⏳ | |

---

## Execution Order

1. **Authentication tests** (1.1-1.3) - 5 minutes
2. **Endpoint smoke tests** (6.1-6.4) - 10 minutes
3. **Error handling** (7.1-7.3) - 5 minutes
4. **Agent memory** (4.1-4.2) - 10 minutes
5. **Knowledge cache** (5.1-5.2) - 10 minutes
6. **Transaction safety** (3.1-3.2) - 10 minutes
7. **Rate limiting** (2.1-2.2) - 15 minutes
8. **File upload security** (8.1-8.3) - 10 minutes

**Total Estimated Time**: 75 minutes

---

## Success Criteria

- ✅ All auth tests pass
- ✅ Rate limiting triggers correctly
- ✅ Transactions commit/rollback properly
- ✅ Agent memory persists
- ✅ Cache improves performance
- ✅ All endpoints return expected responses
- ✅ Error handling works correctly
- ✅ File upload security enforced

**Target**: 100% test pass rate
