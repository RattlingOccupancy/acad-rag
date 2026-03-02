"""
This module defines the FastAPI web server for the RAG application.
It provides endpoints for uploading files, asking questions, and system health checks.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.rag_pipeline import ask, initialize_runtime, reset_runtime
from backend.ingestion.ingest import run_ingestion
from backend.retrieval.embed_store import build_vector_index


from backend.config import VECTOR_EMBEDDING_STORAGE_DIR, UPLOADS_DIR


# --- Models ---


class AskRequest(BaseModel):
    """Request model for asking a question."""
    query: str = Field(..., min_length=1, description="The user's query")
    retrieval_top_k: int = Field(default=8, ge=1, le=50, description="Initial nodes to retrieve")
    final_top_k: int = Field(default=4, ge=1, le=20, description="Final nodes after reranking")
    use_cache: bool = Field(default=True, description="Whether to use cached results")


class DeleteRequest(BaseModel):
    """Request model for deleting a file."""
    filename: str


class SourceItem(BaseModel):
    """Model representing a single document snippet source."""
    doc: str
    page: str
    snippet: str


class AskResponse(BaseModel):
    """Response model for a query."""
    answer: str
    sources: List[SourceItem]


# --- Helpers ---


def _extract_source_items(final_nodes: List[Any]) -> List[Dict[str, str]]:
    """ Extracts source metadata and snippets from retrieved nodes for the API response. """
    items = []
    seen_snips = set()
    for item in final_nodes:
        node = item.node if hasattr(item, "node") else item
        metadata = getattr(node, "metadata", {}) or {}
        source = metadata.get("source", "unknown")
        page = metadata.get("page_label", "—")
        text = getattr(node, "text", "") or ""
        text = getattr(node, "get_content", lambda: text)()

        if text not in seen_snips:
            seen_snips.add(text)
            items.append({
                "doc": str(source),
                "page": str(page),
                "snippet": text
            })
    return items


# --- FastAPI Setup ---


app = FastAPI(
    title="Academic RAG API",
    description="Backend API for the RAG-based Academic Assistant",
    version="1.0.0"
)

RUNTIME_INIT_ERROR: Optional[str] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clear_json_files(directory: Path) -> None:
    """Truncates all JSON files in a directory instead of deleting the files."""
    if not directory.exists():
        return
    for json_file in directory.glob("*.json"):
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("{}")  # Write empty JSON object


@app.on_event("startup")
def startup_event() -> None:
    """Initializes the backend on startup by clearing old data."""
    global RUNTIME_INIT_ERROR
    try:
        # Clear uploads (actual files)
        if UPLOADS_DIR.exists():
            shutil.rmtree(UPLOADS_DIR, ignore_errors=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        # Clear JSON content in vector_embedding_storage instead of deleting the folder
        _clear_json_files(VECTOR_EMBEDDING_STORAGE_DIR)
        
        RUNTIME_INIT_ERROR = None
    except Exception as exc:
        RUNTIME_INIT_ERROR = str(exc)


# --- Endpoints ---


@app.get("/health")
def health() -> Dict[str, Any]:
    """Returns the health status of the API."""
    if RUNTIME_INIT_ERROR:
        return {"status": "degraded", "runtime_init_error": RUNTIME_INIT_ERROR}
    return {"status": "ok"}


@app.post("/reset")
def reset_endpoint() -> Dict[str, str]:
    """Resets the entire RAG system, clearing contents of JSON indices."""
    try:
        if UPLOADS_DIR.exists():
            shutil.rmtree(UPLOADS_DIR, ignore_errors=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        # Clear JSON content instead of deleting the folder
        _clear_json_files(VECTOR_EMBEDDING_STORAGE_DIR)
        
        reset_runtime(clear_reranker=False)
        return {"status": "success", "message": "Backend reset completely (indices cleared)"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/upload")
async def upload_endpoint(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Uploads multiple PDF files, ingests them, and builds the vector index."""
    try:
        # Clear JSON content instead of deleting the vector_embedding_storage folder
        _clear_json_files(VECTOR_EMBEDDING_STORAGE_DIR)

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        for file in files:
            filename = Path(file.filename or "").name
            if not filename:
                raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Only PDF files allowed: {filename}"
                )

            file_path = UPLOADS_DIR / filename
            with open(file_path, "wb") as f:
                contents = await file.read()
                f.write(contents)

        # Ingest ALL files current in uploads (rebuild everything)
        all_pdf_paths = [str(p) for p in UPLOADS_DIR.glob("*.pdf")]
        nodes = run_ingestion(uploaded_files=all_pdf_paths)
        build_vector_index(nodes)
        
        # Reset runtime to pick up the new index
        reset_runtime()
        initialize_runtime(retrieval_top_k=8)

        # Extract file page counts for the UI
        file_pages = {}
        for node in nodes:
            metadata = getattr(node, "metadata", {}) or {}
            source = metadata.get("source")
            page_label = metadata.get("page_label")
            if source and page_label:
                source_basename = Path(str(source)).name
                try:
                    page_num = int(page_label)
                    file_pages[source_basename] = max(file_pages.get(source_basename, 0), page_num)
                except ValueError:
                    pass

        return_files = [Path(f.filename or "").name for f in files]
        for fname in return_files:
            if fname not in file_pages:
                file_pages[fname] = 1

        return {
            "status": "success",
            "message": f"Uploaded and indexed {len(files)} file(s)",
            "files": return_files,
            "file_pages": file_pages,
            "nodes_created": len(nodes),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/delete")
def delete_endpoint(payload: DeleteRequest) -> Dict[str, str]:
    """Deletes a specific uploaded file and re-builds the index."""
    try:
        filename = payload.filename
        file_path = UPLOADS_DIR / filename

        if file_path.exists():
            file_path.unlink()

        # Clear JSON content instead of deleting the vector_embedding_storage folder
        _clear_json_files(VECTOR_EMBEDDING_STORAGE_DIR)

        reset_runtime()

        # Re-ingest remaining files
        all_pdf_paths = [str(p) for p in UPLOADS_DIR.glob("*.pdf")]
        if all_pdf_paths:
            nodes = run_ingestion(uploaded_files=all_pdf_paths)
            build_vector_index(nodes)
            initialize_runtime(retrieval_top_k=8)
            return {"status": "success", "message": f"Deleted {filename} and re-indexed remainder."}
        
        # If no files left, just clear the index
        build_vector_index([])
        return {"status": "success", "message": f"Deleted {filename}. Database is now empty."}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    """Asks a question against the uploaded documents."""
    try:
        if not UPLOADS_DIR.exists() or not any(UPLOADS_DIR.iterdir()):
            return AskResponse(
                answer="No PDF files uploaded. Please upload files to start a conversation.", 
                sources=[]
            )

        global RUNTIME_INIT_ERROR
        if RUNTIME_INIT_ERROR:
            initialize_runtime(retrieval_top_k=8)
            RUNTIME_INIT_ERROR = None

        answer, _, final_nodes, _ = ask(
            question=payload.query,
            retrieval_top_k=payload.retrieval_top_k,
            final_top_k=payload.final_top_k,
            enable_evaluation=False,
            use_cache=payload.use_cache,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return AskResponse(answer=answer, sources=_extract_source_items(final_nodes))
