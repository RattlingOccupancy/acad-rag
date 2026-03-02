"""
This module provides functionality to generate answers to user questions using retrieved nodes and the Groq LLM.
"""

import os
import sys
from pathlib import Path
from groq import Groq
from generation.prompt import SYSTEM_PROMPT

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Global singleton for the Groq client
client = None


def _load_env_file() -> None:
    """
    Loads environment variables from a .env file located in the project root.
    
    This function manually parses the .env file and updates os.environ if common python-dotenv 
    is not installed or required for minimal dependency overhead.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get_api_key() -> str:
    """
    Retrieves the Groq API key from environment variables.
    
    Returns:
        str: The API key.
    
    Raises:
        RuntimeError: If the API key is not found.
    """
    if "GROQ_API_KEY" not in os.environ:
        _load_env_file()

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")
    return api_key


def get_client() -> Groq:
    """
    Initializes and returns a singleton Groq client.
    
    Returns:
        Groq: An instance of the Groq client.
    """
    global client
    if client is None:
        # Try to disable SSL verification for systems with certificate issues
        os.environ.pop("SSL_CERT_FILE", None)
        client = Groq(api_key=_get_api_key())
    return client


def generate_answer(question: str, nodes: list) -> str:
    """
    Generates an answer to the given question based on provided context nodes using Groq.
    
    Args:
        question (str): The user's query.
        nodes (list): A list of retrieved document nodes containing relevant text.
    
    Returns:
        str: The generated answer text.
    """
    # Build context from retrieved nodes
    context = ""
    for n in nodes:
        context += "- " + n.text + "\n\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nContext:\n{context}",
        },
    ]

    client_instance = get_client()
    response = client_instance.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Using supported Groq model
        messages=messages,
        temperature=0.2,
    )

    return response.choices[0].message.content

