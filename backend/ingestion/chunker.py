from llama_index.core.node_parser import SentenceSplitter

def chunk_documents(documents):
    splitter= SentenceSplitter(
        chunk_size=600,
        chunk_overlap=100
    )
    return splitter.get_nodes_from_documents(documents)