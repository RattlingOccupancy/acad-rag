"""
This module provides document chunking functionality using SentenceSplitter.
"""

from typing import List, Any
from llama_index.core.node_parser import SentenceSplitter


def chunk_documents(documents: List[Any]) -> List[Any]:
    """
    Splits documents into smaller chunks (nodes) based on sentences.

    Args:
        documents (List[Any]): A list of loaded documents.

    Returns:
        List[Any]: A list of chunked nodes.
    """
    splitter = SentenceSplitter(
        chunk_size=600,
        chunk_overlap=100
    )
    return splitter.get_nodes_from_documents(documents)
