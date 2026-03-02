"""
This module provides functionality to load documents from a directory or specific files.
"""

from typing import List, Optional, Any
from llama_index.core import SimpleDirectoryReader


def load_documents(path: str = "data/raw_docs", input_files: Optional[List[str]] = None) -> List[Any]:
    """
    Loads PDF documents using LlamaIndex's SimpleDirectoryReader.

    Args:
        path (str): The directory to search for PDF files if input_files is None.
        input_files (Optional[List[str]]): Specific file paths to load.

    Returns:
        List[Any]: A list of loaded documents.
    """
    if input_files:
        reader = SimpleDirectoryReader(input_files=input_files, required_exts=[".pdf"])
    else:
        reader = SimpleDirectoryReader(
            input_dir=path,
            recursive=True,
            required_exts=[".pdf"],
        )
    return reader.load_data()
