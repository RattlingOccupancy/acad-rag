"""
This module provides text cleaning utilities for document ingestion.
"""

import re


def clean_text(text: str) -> str:
    """
    Cleans the input text by collapsing multiple newlines and extra whitespaces.

    Args:
        text (str): The raw text to clean.

    Returns:
        str: The cleaned text.
    """
    # Replace 3 or more newlines with exactly 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
