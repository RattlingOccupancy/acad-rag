"""
Retrieval evaluation utilities compatible with this project's retrievers.

This module evaluates relevance for nodes returned by:
- backend/retrieval/search.py
- backend/retrieval/hybrid_search.py
- backend/retrieval/reranker.py

It supports both item shapes commonly returned by llama-index pipelines:
- objects with `.text`
- objects with `.node.text` (e.g., NodeWithScore)
"""

import os
import sys
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Ensure project root imports work for direct execution.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None


@dataclass
class RetrievalEvaluation:
    query: str
    num_retrieved: int
    relevance_scores: List[float]
    context_precision: float
    context_recall: float
    avg_relevance: float
    passed_threshold: bool
    details: Dict[str, Any]


class RAGASEvaluator:
    """Cross-encoder based retrieval evaluator."""

    def __init__(
        self,
        relevance_threshold: float = 0.5,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        self.relevance_threshold = relevance_threshold
        self.model_name = model_name
        self.model = None

        if CrossEncoder is not None:
            self.model = CrossEncoder(model_name)

    @staticmethod
    def _unwrap_node(item: Any) -> Any:
        return item.node if hasattr(item, "node") else item

    @classmethod
    def _extract_text(cls, item: Any) -> str:
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

    @classmethod
    def _extract_node_id(cls, item: Any) -> Optional[str]:
        node = cls._unwrap_node(item)
        node_id = getattr(node, "node_id", None)
        if node_id is not None:
            return str(node_id)
        return None

    def evaluate_relevance_simple(
        self,
        query: str,
        retrieved_nodes: Sequence[Any],
    ) -> Optional[RetrievalEvaluation]:
        if self.model is None:
            print("sentence-transformers is not installed. Install it to run evaluation.")
            return None

        nodes = list(retrieved_nodes)
        if not nodes:
            return RetrievalEvaluation(
                query=query,
                num_retrieved=0,
                relevance_scores=[],
                context_precision=0.0,
                context_recall=0.0,
                avg_relevance=0.0,
                passed_threshold=False,
                details={
                    "method": "cross_encoder",
                    "model": self.model_name,
                    "num_relevant": 0,
                    "threshold": self.relevance_threshold,
                    "node_scores": [],
                },
            )

        pairs: List[Tuple[str, str]] = []
        for item in nodes:
            pairs.append((query, self._extract_text(item)))

        raw_scores = self.model.predict(pairs)
        relevance_scores = [float(score) for score in raw_scores]

        num_relevant = sum(score >= self.relevance_threshold for score in relevance_scores)
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        context_precision_value = num_relevant / len(relevance_scores)
        passed_threshold = context_precision_value >= 0.5

        node_scores: List[Dict[str, Any]] = []
        for item, score in zip(nodes, relevance_scores):
            text_preview = self._extract_text(item)
            text_preview = (text_preview[:100] + "...") if len(text_preview) > 100 else text_preview
            node_scores.append(
                {
                    "node_id": self._extract_node_id(item),
                    "text": text_preview,
                    "score": score,
                    "relevant": score >= self.relevance_threshold,
                }
            )

        return RetrievalEvaluation(
            query=query,
            num_retrieved=len(nodes),
            relevance_scores=relevance_scores,
            context_precision=context_precision_value,
            context_recall=0.0,
            avg_relevance=avg_relevance,
            passed_threshold=passed_threshold,
            details={
                "method": "cross_encoder",
                "model": self.model_name,
                "num_relevant": int(num_relevant),
                "threshold": self.relevance_threshold,
                "node_scores": node_scores,
            },
        )

    def filter_by_relevance(
        self,
        query: str,
        retrieved_nodes: Sequence[Any],
        min_relevance: Optional[float] = None,
    ) -> Tuple[List[Any], Optional[RetrievalEvaluation]]:
        nodes = list(retrieved_nodes)
        if not nodes:
            return [], None

        evaluation = self.evaluate_relevance_simple(query, nodes)
        if evaluation is None:
            return nodes, None

        threshold = self.relevance_threshold if min_relevance is None else min_relevance

        filtered_nodes: List[Any] = []
        for item, score in zip(nodes, evaluation.relevance_scores):
            if score >= threshold:
                filtered_nodes.append(item)

        return filtered_nodes, evaluation

    def print_evaluation_report(self, evaluation: Optional[RetrievalEvaluation]) -> None:
        if evaluation is None:
            print("No evaluation available.")
            return

        print("\n" + "=" * 80)
        print("RETRIEVAL EVALUATION REPORT")
        print("=" * 80)
        print(f"\nQuery: {evaluation.query}")
        print(f"Documents Retrieved: {evaluation.num_retrieved}")
        print("\n--- METRICS ---")
        print(f"Context Precision: {evaluation.context_precision:.2%}")
        print(f"Average Relevance: {evaluation.avg_relevance:.3f}")
        print(f"Threshold: {evaluation.details['threshold']}")
        print(f"Relevant Docs: {evaluation.details['num_relevant']}/{evaluation.num_retrieved}")
        print(f"Quality Check: {'PASS' if evaluation.passed_threshold else 'FAIL'}")
        print("\n--- PER DOCUMENT SCORES ---")

        for idx, detail in enumerate(evaluation.details["node_scores"], start=1):
            status = "OK" if detail["relevant"] else "NO"
            print(f"\n[{idx}] {status} Score: {detail['score']:.3f}")
            if detail["node_id"]:
                print(f"Node ID: {detail['node_id']}")
            print(f"Text: {detail['text']}")

        print("\n" + "=" * 80 + "\n")


def _save_evaluation_run(
    query: str,
    evaluation: Optional[RetrievalEvaluation],
    filtered_count: int,
    output_json_path: str,
) -> None:
    run_record: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "filtered_count": filtered_count,
        "evaluation": asdict(evaluation) if evaluation is not None else None,
    }

    output_dir = os.path.dirname(output_json_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    existing_data: Dict[str, Any] = {"runs": []}
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("runs"), list):
                existing_data = loaded
        except (json.JSONDecodeError, OSError):
            pass

    existing_data["runs"].append(run_record)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=True)


def evaluate_retrieval(
    query: str,
    retrieved_nodes: Sequence[Any],
    relevance_threshold: float = 0.5,
    print_report: bool = True,
    min_relevance: Optional[float] = None,
    save_to_json: bool = True,
    output_json_path: str = "backend/retrieval/ragas_eval_runs.json",
) -> Tuple[List[Any], Optional[RetrievalEvaluation]]:
    evaluator = RAGASEvaluator(relevance_threshold=relevance_threshold)
    filtered_nodes, evaluation = evaluator.filter_by_relevance(
        query=query,
        retrieved_nodes=retrieved_nodes,
        min_relevance=min_relevance,
    )

    if print_report:
        evaluator.print_evaluation_report(evaluation)

    if save_to_json:
        _save_evaluation_run(
            query=query,
            evaluation=evaluation,
            filtered_count=len(filtered_nodes),
            output_json_path=output_json_path,
        )

    return filtered_nodes, evaluation


if __name__ == "__main__":
    from backend.retrieval.hybrid_search import HybridRetriever
    from backend.retrieval.reranker import Reranker

    query = "blockchain"

    hybrid = HybridRetriever(top_k=8)
    candidates = hybrid.retrieve(query)

    filtered, evaluation = evaluate_retrieval(
        query=query,
        retrieved_nodes=candidates,
        relevance_threshold=0.5,
        print_report=True,
    )

    reranker = Reranker()
    final_nodes = reranker.rerank(query, filtered, top_k=5)

    print("Final reranked results:")
    for i, item in enumerate(final_nodes, start=1):
        text = RAGASEvaluator._extract_text(item)
        node = RAGASEvaluator._unwrap_node(item)
        metadata = getattr(node, "metadata", {}) or {}
        print(f"\n--- Result {i} ---")
        print(text[:300])
        print("SOURCE:", metadata.get("source"))
