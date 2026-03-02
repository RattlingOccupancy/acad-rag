"""
This module provides the evaluation system for the RAG pipeline.
It uses custom metrics (Precision, Recall, Hit Rate) and a Cross-Encoder for relevance scoring.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pathlib import Path

# Ensure project root imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

from backend.ingestion.ingest import run_ingestion
from backend.retrieval.embed_store import build_vector_index
from backend.retrieval.hybrid_search import HybridRetriever


@dataclass
class RetrievalEvaluation:
    """Dataclass to hold the results of a retrieval evaluation."""
    query: str
    num_retrieved: int
    context_precision: float
    context_recall: float
    hit_rate: float
    avg_relevance: float
    passed_threshold: bool
    details: Dict[str, Any]


class RobustEvaluator:
    """Enhanced RAG evaluator with robust metrics and thresholding."""

    def __init__(
        self,
        relevance_threshold: float = 0.5,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        """
        Initializes the RobustEvaluator.

        Args:
            relevance_threshold (float): Score above which a document is considered relevant.
            model_name (str): Name of the Cross-Encoder model to use.
        """
        self.relevance_threshold = relevance_threshold
        self.model_name = model_name
        self.model = None

        if CrossEncoder is not None:
            try:
                self.model = CrossEncoder(model_name)
            except Exception as e:
                print(f"Warning: Could not load CrossEncoder model: {e}")

    @staticmethod
    def _unwrap_node(item: Any) -> Any:
        """Unwraps a LlamaIndex node from its wrapper if necessary."""
        return item.node if hasattr(item, "node") else item

    @classmethod
    def _extract_text(cls, item: Any) -> str:
        """Extracts text content from a node."""
        node = cls._unwrap_node(item)
        text = getattr(node, "text", None)
        if isinstance(text, str) and text.strip():
            return text
        
        get_content = getattr(node, "get_content", None)
        if callable(get_content):
            try:
                extracted = get_content(metadata_mode="none")
            except TypeError:
                extracted = get_content()
            if isinstance(extracted, str):
                return extracted
        return ""

    def calculate_context_recall(self, query: str, retrieved_texts: List[str]) -> float:
        """
        Calculates a simplified keyword-based context recall.

        Args:
            query (str): The search query.
            retrieved_texts (List[str]): List of retrieved document texts.

        Returns:
            float: Recall score.
        """
        query_words = set(query.lower().split())
        if not query_words:
            return 0.0
        
        combined_text = " ".join(retrieved_texts).lower()
        found_words = [word for word in query_words if word in combined_text]
        return len(found_words) / len(query_words)

    def evaluate_query(
        self,
        query: str,
        retrieved_nodes: Sequence[Any],
    ) -> Optional[RetrievalEvaluation]:
        """
        Evaluates retrieval results for a single query.

        Args:
            query (str): The search query.
            retrieved_nodes (Sequence[Any]): The nodes returned by the retriever.

        Returns:
            Optional[RetrievalEvaluation]: The evaluation results or None if model unavailable.
        """
        if self.model is None:
            print("Cross-encoder model not available for evaluation.")
            return None

        nodes = list(retrieved_nodes)
        if not nodes:
            return RetrievalEvaluation(
                query=query,
                num_retrieved=0,
                context_precision=0.0,
                context_recall=0.0,
                hit_rate=0.0,
                avg_relevance=0.0,
                passed_threshold=False,
                details={"error": "No nodes retrieved"}
            )

        retrieved_texts = [self._extract_text(n) for n in nodes]
        pairs = [(query, text) for text in retrieved_texts]
        
        # Cross-encoder scores
        scores = self.model.predict(pairs)
        relevance_scores = [float(s) for s in scores]
        
        # Metrics calculation
        num_relevant = sum(1 for s in relevance_scores if s >= self.relevance_threshold)
        context_precision = num_relevant / len(nodes)
        context_recall = self.calculate_context_recall(query, retrieved_texts)
        hit_rate = 1.0 if num_relevant > 0 else 0.0
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        passed_threshold = context_precision >= 0.5

        node_details = []
        for i, (node, score) in enumerate(zip(nodes, relevance_scores)):
            node_details.append({
                "rank": i + 1,
                "score": score,
                "is_relevant": score >= self.relevance_threshold,
                "text_snippet": self._extract_text(node)[:200] + "..."
            })

        return RetrievalEvaluation(
            query=query,
            num_retrieved=len(nodes),
            context_precision=context_precision,
            context_recall=context_recall,
            hit_rate=hit_rate,
            avg_relevance=avg_relevance,
            passed_threshold=passed_threshold,
            details={
                "threshold": self.relevance_threshold,
                "num_relevant": num_relevant,
                "node_results": node_details
            }
        )


# Compatibility Aliases and Functions
RAGASEvaluator = RobustEvaluator


def evaluate_retrieval(
    query: str,
    retrieved_nodes: Sequence[Any],
    relevance_threshold: float = 0.5,
    print_report: bool = True,
    save_to_json: bool = True,
    output_json_path: str = "evaluation/ragas_eval_runs.json",
) -> Tuple[List[Any], Optional[RetrievalEvaluation]]:
    """
    Compatibility wrapper for rag_pipeline.py to perform evaluation.
    """
    evaluator = RobustEvaluator(relevance_threshold=relevance_threshold)
    evaluation = evaluator.evaluate_query(query, retrieved_nodes)
    
    if evaluation and save_to_json:
        save_evaluation_to_json(evaluation, output_json_path)
        
    return list(retrieved_nodes), evaluation


def select_files() -> List[str]:
    """Opens a file dialog to select PDF files for evaluation."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_paths = filedialog.askopenfilenames(
        title="Select PDF files for evaluation",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    root.destroy()
    return list(file_paths)


def save_evaluation_to_json(eval_data: RetrievalEvaluation, file_path: str = "evaluation/ragas_eval_runs.json"):
    """Saves evaluation results to a JSON file."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation": asdict(eval_data)
    }
    
    data = {"runs": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    data["runs"].append(record)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    """CLI entry point for running the evaluation system."""
    print("--- RAG Evaluation System ---")
    
    # 1. File Upload
    print("\nPlease select PDF files to upload...")
    files = select_files()
    if not files:
        print("No files selected. Exiting.")
        return
    
    print(f"Selected {len(files)} files: {[os.path.basename(f) for f in files]}")
    
    # 2. Ingestion
    print("\nProcessing documents...")
    try:
        nodes = run_ingestion(uploaded_files=files)
        build_vector_index(nodes)
        print("Ingestion and indexing complete.")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return

    # 3. Evaluation Loop
    evaluator = RobustEvaluator(relevance_threshold=0.5)
    retriever = HybridRetriever(top_k=5)

    while True:
        query = input("\nEnter evaluation query (or 'exit' to quit): ").strip()
        if query.lower() == 'exit':
            break
        if not query:
            continue

        print(f"Evaluating: '{query}'...")
        retrieved_nodes = retriever.retrieve(query)
        evaluation = evaluator.evaluate_query(query, retrieved_nodes)

        if evaluation:
            print("\n" + "="*30)
            print("EVALUATION RESULTS")
            print("="*30)
            print(f"Query: {evaluation.query}")
            print(f"Context Precision: {evaluation.context_precision:.2f}")
            print(f"Context Recall: {evaluation.context_recall:.2f}")
            print(f"Hit Rate: {evaluation.hit_rate:.2f}")
            print(f"Overall Quality: {'PASS' if evaluation.passed_threshold else 'FAIL'}")
            print("-" * 30)
            print(f"Retrieved {evaluation.num_retrieved} documents.")
            
            for doc in evaluation.details.get("node_results", []):
                status = "[RELEVANT]" if doc["is_relevant"] else "[NOT RELEVANT]"
                print(f"\nRank {doc['rank']} {status} (Score: {doc['score']:.2f})")
                print(f"Text: {doc['text_snippet']}")
            
            save_evaluation_to_json(evaluation)
            print(f"\nResults saved to evaluation/ragas_eval_runs.json")
        else:
            print("Evaluation failed.")


if __name__ == "__main__":
    main()
