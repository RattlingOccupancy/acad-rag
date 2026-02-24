from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def build_vector_index(nodes):
    embed_model= HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5",
        device="cpu"
    )
    index= VectorStoreIndex(
        nodes,
        embed_model= embed_model
    )
    index.storage_context.persist(persist_dir="./storage")
    return index





