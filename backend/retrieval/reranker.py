"""
This module provides a reranking component using a Cross-Encoder model.
"""

from typing import List, Any
from sentence_transformers import CrossEncoder


class Reranker:
    """
    Reranks retrieved nodes based on their relevance to the query using a Cross-Encoder.
    """

    def __init__(self):
        """
        Initializes the Reranker with a pre-trained Cross-Encoder model.
        """
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query: str, nodes: List[Any], top_k: int = 5) -> List[Any]:
        """
        Reranks a list of nodes for a given query.

        Args:
            query (str): The search query.
            nodes (List[Any]): List of nodes to rerank.
            top_k (int): Number of top-ranked nodes to return.

        Returns:
            List[Any]: The top-k reranked nodes.
        """
        if not nodes:
            return []

        # Prepare pairs for the Cross-Encoder
        pairs = [(query, n.text) for n in nodes]

        # Predict relevance scores
        scores = self.model.predict(pairs)

        # Sort nodes by score in descending order
        scored_nodes = sorted(zip(nodes, scores), key=lambda x: x[1], reverse=True)

        # Return the top-k nodes
        return [node for node, score in scored_nodes[:top_k]]
