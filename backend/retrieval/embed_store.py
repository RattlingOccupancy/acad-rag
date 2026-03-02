"""
This module provides functionality to build and persist a LlamaIndex vector store.
"""

from typing import List, Any
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


from backend.config import VECTOR_EMBEDDING_STORAGE_DIR


def build_vector_index(nodes: List[Any]) -> VectorStoreIndex:
    """
    Builds a vector store index from a list of nodes and persists it to disk.

    Args:
        nodes (List[Any]): A list of document nodes to index.

    Returns:
        VectorStoreIndex: The created vector store index.
    """
    # Initialize the embedding model
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5",
        device="cpu"
    )

    # Create the index from nodes
    index = VectorStoreIndex(
        nodes,
        embed_model=embed_model
    )

    # Persist the index to the centralized root vector_embedding_storage directory
    index.storage_context.persist(persist_dir=str(VECTOR_EMBEDDING_STORAGE_DIR))
    
    return index
