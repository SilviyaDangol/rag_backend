from pinecone import Pinecone
from config import Config

pc = Pinecone(api_key=Config.PINECONE_DEFAULT_API)
index = pc.Index(Config.PINECONE_INDEX_NAME)

def upstream_pine_code(vector_embeddings):
    index.upsert(vectors=vector_embeddings)
    return True

def query_top2(vector_embedding, metadata_filter: dict | None = None):
    if hasattr(vector_embedding, "tolist"):
        vector_embedding = vector_embedding.tolist()

    response = index.query(
        vector=vector_embedding,
        top_k=2,
        include_metadata=True,
        filter=metadata_filter,
    )

    return [
        {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata
        }
        for match in response.matches
    ]

