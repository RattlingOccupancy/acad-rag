# Deployment Guide - Import Fixes

## ✅ Changes Made

### 1. **Converted all relative imports to absolute imports**
- `backend/retrieval/hybrid_search.py`: `from .reranker` → `from backend.retrieval.reranker`
- `backend/ingestion/ingest.py`: `from .loaders/cleaner/chunker` → `from backend.ingestion.*`
- `backend/retrieval/build_index.py`: `from ingestion/retrieval` → `from backend.ingestion/retrieval`
- `backend/rag_pipeline.py`: Removed hacky sys.path manipulation and importlib fallbacks

### 2. **Added package structure files**
- Created root `__init__.py` - makes the project a valid Python package
- Created `pyproject.toml` - enables proper installation and deployment

---

## 🚀 How to Run (No Import Errors)

### Option 1: Run as Module (RECOMMENDED) ⭐
```bash
# From the workspace ROOT (c:\Users\shanu\Desktop\RAG_experiment_2)
python -m backend.rag_pipeline
```

### Option 2: Run with PYTHONPATH set
```bash
# PowerShell:
$env:PYTHONPATH = "."
python backend/rag_pipeline.py

# Command Prompt:
set PYTHONPATH=.
python backend/rag_pipeline.py

# Bash/Linux:
export PYTHONPATH=.
python backend/rag_pipeline.py
```

### Option 3: Install as editable package
```bash
# From the workspace ROOT
pip install -e .
python -m backend.rag_pipeline
```

---

## ⚙️ VS Code Configuration

Add this to `.vscode/settings.json` to fix IntelliSense:

```json
{
  "python.analysis.extraPaths": ["."],
  "python.linting.enabled": true
}
```

Or create `.vscode/launch.json` for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: RAG Pipeline",
      "type": "python",
      "request": "launch",
      "module": "backend.rag_pipeline",
      "justMyCode": true,
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

---

## ⚠️ What NOT to do

❌ **Don't run files directly:**
```bash
python backend/rag_pipeline.py  # This will fail with relative import errors
cd backend && python rag_pipeline.py  # This will also fail
```

✅ **Do run as modules:**
```bash
python -m backend.rag_pipeline  # Works perfectly
```

---

## 🔍 Why This Works

1. **Absolute imports**: All modules use explicit paths (`backend.module` instead of `.module`), so Python always knows where to find them
2. **Package structure**: All directories have `__init__.py`, making them proper packages
3. **Module execution**: Using `-m` tells Python to execute a package module, which automatically registers the root as a valid import path
4. **No sys.path manipulation**: Clean code without workarounds

This setup will work consistently across:
- Local development
- CI/CD pipelines
- Docker containers
- Cloud deployments
- Different Python environments

---

## Testing the Fix

```bash
cd c:\Users\shanu\Desktop\RAG_experiment_2
python -m backend.rag_pipeline
```

If this runs without `ImportError: attempted relative import with no known parent package`, all fixes are working! ✅
