import sys
import os
from pathlib import Path
from typing import Iterable, List, Optional

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.ingestion.loaders import load_documents
from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import chunk_documents


def _normalize_paths(paths: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if p.exists() and p.is_file():
            normalized.append(str(p))
    return normalized


def run_ingestion(
    path: str = "data/raw_docs",
    uploaded_files: Optional[List[str]] = None,
):
    input_files: Optional[List[str]] = None
    if uploaded_files:
        normalized_files = _normalize_paths(uploaded_files)
        pdf_files = [f for f in normalized_files if Path(f).suffix.lower() == ".pdf"]
        input_files = pdf_files

    docs = load_documents(path=path, input_files=input_files)

    for d in docs:
        d.set_content(clean_text(d.text))
        d.metadata["source"] = d.metadata.get("file_name", "unknown")
        d.metadata["subject"] = "Cloud Computing"

    nodes = chunk_documents(docs)

    print(f"total chunks created: {len(nodes)}")
    if nodes:
        print("Sample node metadata:")
        print(nodes[0].metadata)

    return nodes


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ingestion for local folder or uploaded files.")
    parser.add_argument(
        "--path",
        default="data/raw_docs",
        help="Directory to ingest when --files is not provided.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="One or more uploaded PDF file paths (.pdf only).",
    )

    args = parser.parse_args()
    run_ingestion(
        path=args.path,
        uploaded_files=args.files,
    )
