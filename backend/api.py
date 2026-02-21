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


class AskResponse(BaseModel):
    answer: str
    sources: List[str]


def _extract_unique_sources(final_nodes: List[object]) -> List[str]:
    unique_sources: List[str] = []
    for item in final_nodes:
        node = item.node if hasattr(item, "node") else item
        metadata = getattr(node, "metadata", {}) or {}
        source = metadata.get("source", "unknown")
        if source not in unique_sources:
            unique_sources.append(source)
    return unique_sources


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


@app.on_event("startup")
def startup_event() -> None:
    # Warm the runtime once so first user request is faster.
    global RUNTIME_INIT_ERROR
    try:
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


@app.post("/upload")
async def upload_endpoint(files: List[UploadFile] = File(...)) -> dict:
    """Upload PDF files and ingest them into the RAG system."""
    try:
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

        return {
            "status": "success",
            "message": f"Uploaded and indexed {len(files)} file(s)",
            "files": [Path(f.filename or "").name for f in files],
            "nodes_created": len(nodes),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    try:
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

    return AskResponse(answer=answer, sources=_extract_unique_sources(final_nodes))
