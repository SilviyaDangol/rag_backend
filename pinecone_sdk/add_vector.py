from pinecone import Pinecone
from config import Config

pc = Pinecone(api_key=Config.PINECONE_DEFAULT_API)
index = pc.Index(Config.PINECONE_INDEX_NAME)

def upstream_pine_code(vector_embeddings):
    index.upsert(vectors=vector_embeddings)
    return True



