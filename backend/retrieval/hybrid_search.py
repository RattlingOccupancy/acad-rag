import sys
import os

# Set up path BEFORE imports so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.retrieval.reranker import Reranker
from rank_bm25 import BM25Okapi
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import re

def tokenize(text):
    return re.findall(r"\w+", text.lower())

class HybridRetriever:
    def __init__(self, top_k=5):
        self.top_k= top_k

        embed_model= HuggingFaceEmbedding(
            model_name= "BAAI/bge-small-en-v1.5"
        )  

        storage_context= StorageContext.from_defaults(
            persist_dir= "./storage"
        )

        self.index= load_index_from_storage(
            storage_context,
            embed_model= embed_model
        )

        self.nodes= list(self.index.docstore.docs.values())

        tokenized= [tokenize(n.text) for n in self.nodes]
        self.bm25= BM25Okapi((tokenized))

    def retrieve(self, query):
        # Dense retrieval
        dense_results = self.index.as_retriever(
            similarity_top_k=self.top_k
        ).retrieve(query)

        # Sparse retrieval
        tokenized_query = tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)

        top_sparse_idx = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:self.top_k]

        sparse_results = [self.nodes[i] for i in top_sparse_idx]

        # Merge (union)
        combined = {n.node_id: n for n in dense_results}

        for n in sparse_results:
            combined[n.node_id] = n

        return list(combined.values())        
    
# ✅ PIPELINE CONTROL HERE
if __name__ == "__main__":
    query = "deep learning"

    hybrid_retriever = HybridRetriever(top_k=8)
    reranker = Reranker()

    # recall stage
    candidates = hybrid_retriever.retrieve(query)

    # ranking stage
    final_nodes = reranker.rerank(query, candidates, top_k=5)

    for i, r in enumerate(final_nodes):
        print(f"\n--- Result {i+1} ---")
        print(r.text[:300])
        print("SOURCE:", r.metadata.get("source"))
