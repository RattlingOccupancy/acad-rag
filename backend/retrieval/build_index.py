import sys
import os

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.ingestion.ingest import run_ingestion
from backend.retrieval.embed_store import build_vector_index

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build vector index from folder or uploaded files.")
    parser.add_argument(
        "--path",
        default="data/raw_docs",
        help="Directory to ingest when --files is not provided.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="One or more uploaded file paths (.pdf/.docx/.doc).",
    )
    parser.add_argument(
        "--convert-word-to-pdf",
        action="store_true",
        help="Convert Word files to PDF before ingestion (requires docx2pdf).",
    )
    parser.add_argument(
        "--converted-pdf-dir",
        default="data/uploaded_pdfs",
        help="Output folder for converted PDFs.",
    )

    args = parser.parse_args()

    nodes = run_ingestion(
        path=args.path,
        uploaded_files=args.files,
        convert_word_to_pdf=args.convert_word_to_pdf,
        converted_pdf_dir=args.converted_pdf_dir,
    )
    index= build_vector_index(nodes)
    print("vector index successfully built.")
