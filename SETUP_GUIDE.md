# RAG System Setup Guide

## Overview

Your RAG system now has a complete FastAPI backend and React frontend with file upload and query capabilities.

---

## Backend Setup (FastAPI)

### File: `backend/api.py`

**Key Components:**

1. **CORS Middleware** - Allows frontend requests from `localhost:5173` and `localhost:3000`
2. **Health Check** (`GET /health`) - Verifies backend status
3. **Upload Endpoint** (`POST /upload`) - Accepts multiple PDF files
4. **Ask Endpoint** (`POST /ask`) - Queries the RAG system

### Running the Backend

```bash
cd "backend"
pip install fastapi uvicorn python-multipart
uvicorn api:app --reload --port 8000
```

The server will start at `http://localhost:8000`

### API Endpoints

#### 1. Upload Files
```
POST /upload
Content-Type: multipart/form-data

Request:
  - files: [PDF files]

Response:
{
  "status": "success",
  "message": "Uploaded and indexed 2 file(s)",
  "files": ["document1.pdf", "document2.pdf"],
  "nodes_created": 45
}
```

#### 2. Query RAG System
```
POST /ask
Content-Type: application/json

Request:
{
  "query": "What is binary search?",
  "retrieval_top_k": 8,
  "final_top_k": 4,
  "use_cache": true
}

Response:
{
  "answer": "Binary search is a fast algorithm...",
  "sources": ["document1.pdf", "document2.pdf"]
}
```

#### 3. Health Check
```
GET /health

Response (success):
{
  "status": "ok"
}

Response (degraded):
{
  "status": "degraded",
  "runtime_init_error": "Error message"
}
```

---

## Frontend Setup (React + Vite)

### Files Created

1. **`src/api.js`** - API client helper functions
   - `uploadFiles(files)` - Upload PDFs to backend
   - `askRAG(query)` - Send query to RAG system
   - `checkHealth()` - Check backend status

2. **`src/FileUpload.jsx`** - File upload component (optional)
   - Handles file selection
   - Shows loading/error states

3. **`src/QueryInput.jsx`** - Query input component (optional)
   - Text input with submit button
   - Loading state management

4. **`src/AnswerDisplay.jsx`** - Answer display component (optional)
   - Shows RAG answer
   - Lists sources

5. **`src/Dashboard.jsx`** - Updated with backend integration
   - Calls `uploadFiles()` when user selects files
   - Calls `askRAG()` when user submits query
   - Displays real RAG results

### Running the Frontend

```bash
cd "frontend"
npm install
npm run dev
```

Frontend will be at `http://localhost:5173`

### Environment Variables

Create `.env` file in `frontend/`:
```
VITE_API_URL=http://localhost:8000
```

Or use default (localhost:8000)

---

## How It Works

### File Upload Flow

1. **User selects PDFs** in "Upload" tab
2. **Frontend sends to** `POST /upload`
3. **Backend:**
   - Saves files to `data/uploads/`
   - Runs ingestion: `run_ingestion(uploaded_files=[...])`
   - Chunks documents
   - Builds/rebuilds vector index in `storage/`
   - Returns nodes created count
4. **Frontend updates** document list to "indexed"

### Query Flow

1. **User types question** and submits
2. **Frontend sends to** `POST /ask`
3. **Backend:**
   - Retrieves context with `ask()` function
   - Uses RAG pipeline: retrieval → reranking → generation
   - Returns answer + source documents
4. **Frontend displays** answer with source citations

---

## Component Structure

### `api.js` (API Client)
```javascript
uploadFiles(files)        // Upload PDFs
askRAG(query)             // Query the system
checkHealth()             // Check backend status
```

### Dashboard Integration
```
User types in textarea
    ↓
submit (send button)
    ↓
add user message to chat
    ↓
call askRAG(query)
    ↓
display assistant response + sources
```

---

## Troubleshooting

### "Backend unreachable"
- Ensure FastAPI is running: `uvicorn api:app --reload --port 8000`
- Check CORS origins in `api.py`
- Frontend might be on different port, use proxy (Vite config has it)

### Upload not working
- Ensure `data/uploads/` directory exists
- Check PDF file extension
- Verify backend is ingesting files correctly

### No answer returned
- Check if documents are indexed (Documents tab shows "Indexed")
- Verify RAG pipeline is working: test with `python backend/rag_pipeline.py`
- Check backend logs for errors

### Slow first query
- First query might be slow due to runtime initialization
- Subsequent queries should be faster (cached)
- Use `/health` endpoint to check status

---

## Production Deployment

### Backend
```bash
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend
```bash
npm run build
# Deploy dist/ folder to static host (Vercel, Netlify, etc)
# Update VITE_API_URL to production backend URL
```

### Docker (Optional)

Create `backend/Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Key Changes Made

✅ **api.py** - Added `/upload` endpoint + imports
✅ **Dashboard.jsx** - Connected to backend API
✅ **api.js** - Created API client functions
✅ **vite.config.js** - Added proxy for development
✅ **FileUpload.jsx** - Optional file upload component
✅ **QueryInput.jsx** - Optional query component
✅ **AnswerDisplay.jsx** - Optional answer display component

All files are ready to use. Start backend and frontend, upload PDFs, and ask questions!
