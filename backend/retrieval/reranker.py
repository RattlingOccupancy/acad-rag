from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self):
        self.model= CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query, nodes, top_k=5):
        pairs= []
        for n in nodes:
            pairs.append((query, n.text))

        scores= self.model.predict(pairs)

        scored= []
        for node, score in zip(nodes, scores):
            scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        top_nodes= []
        for node, _ in scored[:top_k]:
            top_nodes.append(node)

        return top_nodes