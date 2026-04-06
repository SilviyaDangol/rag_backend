from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')

def get_vector_embeddings(sentences):
    embeddings = model.encode(sentences)
    return embeddings
