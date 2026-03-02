
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os
import sys

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


try:
    from backend.ingestion.ingest import run_ingestion
    from backend.retrieval.embed_store import build_vector_index
    from backend.config import VECTOR_EMBEDDING_STORAGE_DIR
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from ingestion.ingest import run_ingestion
    from retrieval.embed_store import build_vector_index

def load_index():
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5",
        device="cpu"
    )
    vector_embedding_storage_context = StorageContext.from_defaults(persist_dir=str(VECTOR_EMBEDDING_STORAGE_DIR))

    # Check if index exists, if not build it
    try:
        return load_index_from_storage(
            vector_embedding_storage_context,
            embed_model=embed_model
        )
    except ValueError:
        print("Index not found. Building index...")
        nodes = run_ingestion()
        index = build_vector_index(nodes)
        return index


def search(query):
    index = load_index()
    retriever = index.as_retriever(similarity_top_k=5)
    nodes = retriever.retrieve(query)
    return nodes


if __name__ == "__main__":
    results = search("Cloud computing charges")

    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(r.node.text[:300])
        print("SOURCE:", r.node.metadata.get("source"))
