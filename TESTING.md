# Testing Your RAG Application

## Quick Test Script

### Option 1: Windows Batch
Run this to start both services:
```bash
cd c:\Users\shanu\Desktop\RAG_experiment_2_deploy_maybe final
start.bat
```

### Option 2: macOS/Linux
```bash
cd ~/Desktop/"RAG_experiment_2_deploy_maybe final"
chmod +x start.sh
./start.sh
```

### Option 3: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
pip install fastapi uvicorn python-multipart
uvicorn api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Test Checklist

### ✅ Backend Running
- Visit http://localhost:8000/docs
- You should see **Swagger API documentation**
- Try `/health` endpoint → should return `{"status": "ok"}`

### ✅ Frontend Running
- Visit http://localhost:5173
- You should see the **ScholArx dashboard**
- Document list shows on left sidebar

### ✅ File Upload Test

1. Click **"Upload"** tab in left sidebar
2. Click **"Browse Files"** or drag PDF files
3. Select a PDF from your system
4. See loading indicator (status changes to "processing" → "indexed")
5. Check sidebar stats: "Indexed" count increases

**Expected Response:**
```json
{
  "status": "success",
  "message": "Uploaded and indexed 1 file(s)",
  "files": ["document.pdf"],
  "nodes_created": 42
}
```

### ✅ Query Test

1. In chat area, type a question: `"What is in this document?"`
2. Click **"Ask"** button or press Ctrl+Enter
3. See loading indicator (three dots "...")
4. Response appears in chat with sources

**Expected Flow:**
```
User: "What is binary search?"
    ↓ (sent to backend /ask)
Backend: retrieves context, generates answer
    ↓
UI: displays answer + source citations
```

### ✅ API Testing with curl

**Test Health:**
```bash
curl http://localhost:8000/health
```

**Upload File:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@path/to/document.pdf"
```

**Ask Question:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "retrieval_top_k": 8,
    "final_top_k": 4
  }'
```

---

## Common Issues & Solutions

### Frontend says "Backend unreachable"
**Solution:**
1. Ensure backend is running on port 8000
2. Check CORS origins in `backend/api.py` (line 35-41)
3. Try visiting http://localhost:8000/health directly
4. Check browser console for CORS errors

### Upload fails with "Only PDF files allowed"
**Solution:**
- Currently only `.pdf` extension is allowed
- Ensure file is valid PDF
- To allow other formats, edit `api.py` line 78-80

### First query is very slow
**Solution:**
- First request initializes the runtime (loads models, etc.)
- Completely normal - can take 10-30 seconds
- Check `/health` endpoint - it will show `"degraded"` until ready
- Subsequent queries will be much faster due to caching

### No answer, just empty response
**Solution:**
1. Ensure documents are uploaded and indexed
2. Check sidebar - should show "Indexed" documents
3. Try simple query: `"test"`
4. Check backend logs for errors
5. Verify RAG pipeline works independently

### Port already in use
**Solution:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # macOS/Linux

# Kill the process or use different port
uvicorn api:app --port 8001
```

---

## File Structure for Reference

```
backend/
├── api.py                 # FastAPI app with 3 endpoints
├── rag_pipeline.py        # Your RAG logic
├── ingestion/             # Document processing
└── retrieval/             # Vector search + reranking

frontend/
├── src/
│   ├── api.js            # API client (NEW)
│   ├── Dashboard.jsx     # Updated with API calls
│   ├── FileUpload.jsx    # Optional component
│   ├── QueryInput.jsx    # Optional component
│   ├── AnswerDisplay.jsx # Optional component
│   └── main.jsx
├── vite.config.js        # Updated with proxy
└── package.json

Root:
├── SETUP_GUIDE.md        # Detailed setup doc
├── TESTING.md            # This file
├── start.sh              # Linux/Mac launcher
└── start.bat             # Windows launcher
```

---

## Next Steps

1. **Upload real documents** from your courses
2. **Test with questions** from those materials
3. **Inspect sources** shown in responses
4. **Monitor confidence levels** (shown in chat)
5. **Adjust parameters:** `retrieval_top_k`, `final_top_k`
6. **Deploy to production** when ready (see SETUP_GUIDE.md)

---

## Debugging Tips

### Check Backend Logs
Terminal 1 (backend) shows:
- Request logs
- Error messages
- Processing status

### Check Frontend Console
F12 → Console tab shows:
- API response details
- Network errors
- State updates

### Test API Directly
Use FastAPI Swagger UI:
1. Go to http://localhost:8000/docs
2. Click on endpoint (e.g., `/ask`)
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"

### Verify Files Are Ingested
Check `backend/data/uploads/` - files should be there
Check `backend/storage/` - index files should exist

---

Good luck! Your RAG system is ready to use. 🚀
