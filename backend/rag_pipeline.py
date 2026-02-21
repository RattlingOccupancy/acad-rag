import sys
import os
import json
import io
import contextlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.ingestion.ingest import run_ingestion
from backend.retrieval.embed_store import build_vector_index
from backend.retrieval.hybrid_search import HybridRetriever
from backend.retrieval.reranker import Reranker
from backend.retrieval.ragas_eval import evaluate_retrieval, RAGASEvaluator
from generation.answer_generator import generate_answer

_RETRIEVER_POOL: Dict[int, HybridRetriever] = {}
_RERANKER: Optional[Reranker] = None
_ASK_CACHE: Dict[Tuple[str, int, int], Tuple[Any, Any, Any, Any]] = {}
_ASK_CACHE_ORDER: List[Tuple[str, int, int]] = []
_ASK_CACHE_MAX_SIZE = 128
_DEFAULT_RETRIEVAL_TOP_K = 8
_DEFAULT_FINAL_TOP_K = 4


class PipelineStageError(Exception):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


@dataclass
class QueryResult:
    answer: str
    retrieved_nodes: List[Any]
    final_nodes: List[Any]
    evaluation: Any = None


def _extract_text(item):
    return RAGASEvaluator._extract_text(item)


def _extract_source(item):
    node = RAGASEvaluator._unwrap_node(item)
    metadata = getattr(node, "metadata", {}) or {}
    return metadata.get("source", "unknown")


def _short_stage_error_message(error: PipelineStageError) -> str:
    return f"Pipeline failed at {error.stage} stage: {error}"


def _serialize_retrieved_nodes(nodes, max_chars=300):
    return [
        {
            "rank": i,
            "source": _extract_source(n),
            "text": _extract_text(n)[:max_chars],
        }
        for i, n in enumerate(nodes, start=1)
    ]


def _capture_output(func, *args, **kwargs):
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        result = func(*args, **kwargs)
    return result, stdout_buffer.getvalue(), stderr_buffer.getvalue()


def _append_run_to_json(
    json_path,
    query,
    answer,
    evaluation,
    retrieved_nodes,
    reranked_nodes,
    setup_info,
    suppressed_logs,
):
    payload = {"runs": []}
    out_path = Path(json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        try:
            with out_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("runs"), list):
                payload = loaded
        except (json.JSONDecodeError, OSError):
            pass

    unique_sources = sorted({_extract_source(n) for n in retrieved_nodes})
    run = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "answer": answer,
        "metrics": None,
        "documents_retrieved": _serialize_retrieved_nodes(retrieved_nodes),
        "final_context_sources": [_extract_source(n) for n in reranked_nodes],
        "unique_sources": unique_sources,
        "setup": setup_info,
        "suppressed_output": suppressed_logs,
    }

    if evaluation is not None:
        run["metrics"] = {
            "documents_retrieved": evaluation.num_retrieved,
            "context_precision": evaluation.context_precision,
            "average_relevance": evaluation.avg_relevance,
            "num_relevant": evaluation.details.get("num_relevant", 0),
            "quality_check": "PASS" if evaluation.passed_threshold else "FAIL",
        }

    payload["runs"].append(run)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)


def _select_files_via_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilenames(
            title="Upload PDF files",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return [p for p in selected if Path(p).suffix.lower() == ".pdf"]
    except Exception as exc:
        print(f"File dialog unavailable: {exc}")
        return []


def _get_valid_pdf_files(file_paths: List[str]) -> List[str]:
    return [p for p in file_paths if Path(p).exists() and Path(p).suffix.lower() == ".pdf"]


def _get_retriever(top_k: int) -> HybridRetriever:
    retriever = _RETRIEVER_POOL.get(top_k)
    if retriever is None:
        retriever = HybridRetriever(top_k=top_k)
        _RETRIEVER_POOL[top_k] = retriever
    return retriever


def _get_reranker() -> Reranker:
    global _RERANKER
    if _RERANKER is None:
        _RERANKER = Reranker()
    return _RERANKER


def initialize_runtime(retrieval_top_k: int = 8) -> None:
    _get_retriever(retrieval_top_k)
    _get_reranker()


def reset_runtime(clear_reranker: bool = False) -> None:
    global _RERANKER
    _RETRIEVER_POOL.clear()
    _ASK_CACHE.clear()
    _ASK_CACHE_ORDER.clear()
    if clear_reranker:
        _RERANKER = None


def _make_cache_key(question: str, retrieval_top_k: int, final_top_k: int) -> Tuple[str, int, int]:
    return (question.strip().lower(), retrieval_top_k, final_top_k)


def _get_cached_result(cache_key: Tuple[str, int, int]) -> Optional[Tuple[Any, Any, Any, Any]]:
    return _ASK_CACHE.get(cache_key)


def _save_cached_result(cache_key: Tuple[str, int, int], result: Tuple[Any, Any, Any, Any]) -> None:
    _ASK_CACHE[cache_key] = result
    _ASK_CACHE_ORDER.append(cache_key)
    if len(_ASK_CACHE_ORDER) > _ASK_CACHE_MAX_SIZE:
        oldest_key = _ASK_CACHE_ORDER.pop(0)
        _ASK_CACHE.pop(oldest_key, None)


def _retrieve_with_fallback(question: str, retrieval_top_k: int) -> List[Any]:
    try:
        return _get_retriever(retrieval_top_k).retrieve(question)
    except Exception:
        fallback_top_k = min(5, retrieval_top_k)
        try:
            return _get_retriever(fallback_top_k).retrieve(question)
        except Exception as exc:
            raise PipelineStageError("retrieval", "could not fetch relevant documents.") from exc


def _evaluate_if_enabled(
    question: str,
    candidates: List[Any],
    enable_evaluation: bool,
) -> Tuple[List[Any], Any]:
    if not enable_evaluation:
        return candidates, None

    try:
        filtered_nodes, evaluation = evaluate_retrieval(
            query=question,
            retrieved_nodes=candidates,
            print_report=False,
            save_to_json=False,
        )
    except Exception:
        return candidates, None

    return filtered_nodes or candidates, evaluation


def _rerank_with_fallback(question: str, nodes: List[Any], final_top_k: int) -> List[Any]:
    if not nodes:
        raise PipelineStageError("reranking", "no documents available after retrieval.")

    try:
        return _get_reranker().rerank(question, nodes, top_k=final_top_k)
    except Exception:
        return nodes[:final_top_k]


def _generate_with_error_context(question: str, final_nodes: List[Any]) -> str:
    if not final_nodes:
        raise PipelineStageError("generation", "no context found to generate an answer.")

    try:
        return generate_answer(question, final_nodes)
    except Exception as exc:
        raise PipelineStageError("generation", "could not generate an answer right now.") from exc


def _setup_index_from_uploaded_files(file_paths: List[str]) -> Tuple[Dict[str, Any], str, str]:
    setup_info = {
        "index_updated_from_upload": False,
        "uploaded_pdf_files": [],
        "total_chunks_created": 0,
        "sample_node_metadata": None,
    }

    valid_files = _get_valid_pdf_files(file_paths)
    if not valid_files:
        return setup_info, "", ""

    try:
        nodes, ingest_stdout, ingest_stderr = _capture_output(
            run_ingestion,
            uploaded_files=valid_files,
        )
    except Exception as exc:
        raise PipelineStageError("ingestion", "could not process uploaded files.") from exc

    try:
        _, index_stdout, index_stderr = _capture_output(build_vector_index, nodes)
    except Exception as exc:
        raise PipelineStageError("ingestion", "index build failed for uploaded files.") from exc

    setup_info = {
        "index_updated_from_upload": True,
        "uploaded_pdf_files": valid_files,
        "total_chunks_created": len(nodes),
        "sample_node_metadata": nodes[0].metadata if nodes else None,
    }
    return setup_info, ingest_stdout + index_stdout, ingest_stderr + index_stderr


def ask(
    question,
    retrieval_top_k=_DEFAULT_RETRIEVAL_TOP_K,
    final_top_k=_DEFAULT_FINAL_TOP_K,
    enable_evaluation=False,
    use_cache=True,
):
    cache_key = _make_cache_key(question, retrieval_top_k, final_top_k)
    if use_cache:
        cached_result = _get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

    candidates = _retrieve_with_fallback(question, retrieval_top_k)
    filtered_nodes, evaluation = _evaluate_if_enabled(question, candidates, enable_evaluation)
    final_nodes = _rerank_with_fallback(question, filtered_nodes, final_top_k)
    answer = _generate_with_error_context(question, final_nodes)

    result_data = QueryResult(
        answer=answer,
        retrieved_nodes=candidates,
        final_nodes=final_nodes,
        evaluation=evaluation,
    )
    result = (
        result_data.answer,
        result_data.retrieved_nodes,
        result_data.final_nodes,
        result_data.evaluation,
    )
    if use_cache:
        _save_cached_result(cache_key, result)

    return result


def run_cli():
    file_paths = _select_files_via_dialog()
    setup_info = {
        "index_updated_from_upload": False,
        "uploaded_pdf_files": [],
        "total_chunks_created": 0,
        "sample_node_metadata": None,
    }
    setup_suppressed_stdout = ""
    setup_suppressed_stderr = ""

    if file_paths:
        try:
            setup_info, setup_suppressed_stdout, setup_suppressed_stderr = _setup_index_from_uploaded_files(file_paths)
        except PipelineStageError as exc:
            print(_short_stage_error_message(exc))
            print("Continuing with existing index.")

    try:
        initialize_runtime(_DEFAULT_RETRIEVAL_TOP_K)
    except Exception:
        pass

    while True:
        query = input("\nEnter your query (or type 'exit'): ").strip()
        if not query:
            print("Empty query. Please enter a valid query.")
            continue
        if query.lower() in {"exit", "quit"}:
            print("Exiting pipeline.")
            break

        try:
            ask_result, ask_stdout, ask_stderr = _capture_output(
                ask,
                query,
                enable_evaluation=True,
                use_cache=False,
            )
            answer, retrieved_nodes, sources, evaluation = ask_result
        except PipelineStageError as exc:
            print(_short_stage_error_message(exc))
            continue
        except Exception:
            print("Pipeline failed at unknown stage: unexpected error.")
            continue

        try:
            _append_run_to_json(
                json_path="backend/retrieval/rag_pipeline_runs.json",
                query=query,
                answer=answer,
                evaluation=evaluation,
                retrieved_nodes=retrieved_nodes,
                reranked_nodes=sources,
                setup_info=setup_info,
                suppressed_logs={
                    "setup_stdout": setup_suppressed_stdout,
                    "setup_stderr": setup_suppressed_stderr,
                    "query_stdout": ask_stdout,
                    "query_stderr": ask_stderr,
                },
            )
        except Exception:
            print("Warning: failed to save this run to JSON log.")

        print("\nLLM response:\n")
        print(answer)


if __name__ == "__main__":
    run_cli()



