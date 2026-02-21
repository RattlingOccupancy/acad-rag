from llama_index.core import SimpleDirectoryReader

def load_documents(path="data/raw_docs", input_files=None):
    if input_files:
        reader = SimpleDirectoryReader(input_files=input_files, required_exts=[".pdf"])
    else:
        reader = SimpleDirectoryReader(
            input_dir=path,
            recursive=True,
            required_exts=[".pdf"],
        )
    return reader.load_data()
