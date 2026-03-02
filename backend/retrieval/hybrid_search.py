"""
This module implements a Hybrid Retriever that combines dense (vector-based) 
and sparse (BM25) retrieval methods.
"""

import sys
import os
import re
from typing import List, Any
from rank_bm25 import BM25Okapi
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


from backend.config import VECTOR_EMBEDDING_STORAGE_DIR


def tokenize(text: str) -> List[str]:
    """
    Tokenizes text into a list of lowercase alphanumeric words.
    
    Args:
        text (str): The text to tokenize.
        
    Returns:
        List[str]: A list of tokens.
    """
    return re.findall(r"\w+", text.lower())


class HybridRetriever:
    """
    A retriever that performs both dense and sparse search and merges the results.
    """

    def __init__(self, top_k: int = 5):
        """
        Initializes the HybridRetriever.

        Args:
            top_k (int): Number of nodes to retrieve from each method.
        """
        self.top_k = top_k

        # Initialize embedding model (dense)
        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
            device="cpu"
        )

        # Load existing index from the centralized root vector_embedding_storage directory
        vector_embedding_storage_context = StorageContext.from_defaults(
            persist_dir=str(VECTOR_EMBEDDING_STORAGE_DIR)
        )

        self.index = load_index_from_storage(
            vector_embedding_storage_context,
            embed_model=embed_model
        )

        # Extract nodes for BM25 (sparse)
        self.nodes = list(self.index.docstore.docs.values())

        if self.nodes:
            tokenized = [tokenize(n.text) for n in self.nodes]
            self.bm25 = BM25Okapi(tokenized)
        else:
            self.bm25 = None

    def retrieve(self, query: str) -> List[Any]:
        """
        Performs hybrid retrieval for the given query.

        Args:
            query (str): The search query.

        Returns:
            List[Any]: A merged list of retrieved nodes.
        """
        if not self.nodes:
            return []

        # 1. Dense retrieval (Vector search)
        dense_results = self.index.as_retriever(
            similarity_top_k=self.top_k
        ).retrieve(query)

        # 2. Sparse retrieval (Keyword search)
        if self.bm25:
            tokenized_query = tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)

            top_sparse_idx = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:self.top_k]

            sparse_results = [self.nodes[i] for i in top_sparse_idx]
        else:
            sparse_results = []

        # 3. Merge (union) dense and sparse results by node_id
        combined = {n.node_id: n for n in dense_results}

        for n in sparse_results:
            combined[n.node_id] = n

        return list(combined.values())


if __name__ == "__main__":
    # Example usage
    from backend.retrieval.reranker import Reranker
    
    test_query = "deep learning"
    hybrid_retriever = HybridRetriever(top_k=3)
    reranker = Reranker()

    # Recall stage
    candidates = hybrid_retriever.retrieve(test_query)

    # Ranking stage
    final_nodes = reranker.rerank(test_query, candidates, top_k=2)

    for i, r in enumerate(final_nodes):
        print(f"\n--- Result {i+1} ---")
        print(r.text[:300])
        print("SOURCE:", r.metadata.get("source"))

