import os
import sys
from pathlib import Path

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from groq import Groq
from generation.prompt import SYSTEM_PROMPT

client = None


def _load_env_file() -> None:
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
    if "GROQ_API_KEY" not in os.environ:
        _load_env_file()

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")
    return api_key

def get_client():
    global client
    if client is None:
        # Try to disable SSL verification for systems with certificate issues
        os.environ.pop("SSL_CERT_FILE", None)
        client = Groq(api_key=_get_api_key())
    return client

def generate_answer(question, nodes):

    context = ""

    for n in nodes:
        context += "- " + n.text + "\n\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""
Question:
{question}

Context:
{context}
"""
        }
    ]

    client_instance = get_client()
    response = client_instance.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Using supported Groq model
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content    
