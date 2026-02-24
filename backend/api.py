

import os
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.rag_pipeline import ask, initialize_runtime, reset_runtime  # noqa: E402
from backend.ingestion.ingest import run_ingestion  # noqa: E402
from backend.retrieval.embed_store import build_vector_index  # noqa: E402


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    retrieval_top_k: int = Field(default=8, ge=1, le=50)
    final_top_k: int = Field(default=4, ge=1, le=20)
    use_cache: bool = True


class SourceItem(BaseModel):
    doc: str
    page: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


def _extract_source_items(final_nodes: List[object]) -> List[dict]:
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
            items.append({"doc": str(source), "page": str(page), "snippet": text})
    return items


app = FastAPI(title="RAG API", version="1.0.0")
RUNTIME_INIT_ERROR = None

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


import shutil

@app.on_event("startup")
def startup_event() -> None:
    # Warm the runtime once so first user request is faster.
    global RUNTIME_INIT_ERROR
    try:
        # Clear out old storage and uploads on fresh start to match frontend
        for d in ["data/uploads", "storage", "backend/storage", "backend/data/uploads"]:
            path = Path(d)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                
        # Initialize an empty vector index so LlamaIndex doesn't crash on load
        build_vector_index([])
        reset_runtime(clear_reranker=False)
        initialize_runtime(retrieval_top_k=8)
        RUNTIME_INIT_ERROR = None
    except Exception as exc:
        # Keep API alive and lazily retry on first ask request.
        RUNTIME_INIT_ERROR = str(exc)


@app.get("/health")
def health() -> dict:
    if RUNTIME_INIT_ERROR:
        return {"status": "degraded", "runtime_init_error": RUNTIME_INIT_ERROR}
    return {"status": "ok"}


@app.post("/reset")
def reset_endpoint() -> dict:
    try:
        for d in ["data/uploads", "storage", "backend/storage", "backend/data/uploads"]:
            path = Path(d)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                
        Path("data/uploads").mkdir(parents=True, exist_ok=True)
        build_vector_index([])
        reset_runtime(clear_reranker=False)
        initialize_runtime(retrieval_top_k=8)
        return {"status": "success", "message": "Backend reset completely"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/upload")
async def upload_endpoint(files: List[UploadFile] = File(...)) -> dict:
    """Upload PDF files and ingest them into the RAG system."""
    try:
        # Strict Replace Mode: completely wipe old database and files on new upload
        for d in ["data/uploads", "storage", "backend/storage", "backend/data/uploads"]:
            path = Path(d)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_paths = []
        for file in files:
            filename = Path(file.filename or "").name
            if not filename:
                raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Only PDF files allowed: {filename}"
                )

            file_path = upload_dir / filename
            with open(file_path, "wb") as f:
                contents = await file.read()
                f.write(contents)
            uploaded_paths.append(str(file_path))

        nodes = run_ingestion(uploaded_files=uploaded_paths)
        build_vector_index(nodes)
        reset_runtime()
        initialize_runtime(retrieval_top_k=8)

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


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    try:
        upload_dir = Path("data/uploads")
        if not upload_dir.exists() or not any(upload_dir.iterdir()):
            return AskResponse(answer="No pdf file uploaded available", sources=[])

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
