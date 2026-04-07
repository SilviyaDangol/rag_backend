import uuid
from fastapi import UploadFile
from sqlmodel import Session
from utils.extractors import TextExtractor
from utils.chunker import TextChunker
from utils.text_embeder import get_vector_embeddings
from pinecone_sdk.add_vector import upstream_pine_code
from db.db import engine
from models.user_metadata import UserMetadataModel


class DocumentConverter:
    def __init__(self, file: UploadFile, name: str, chunk_size: int = 500, overlap: int = 50):
        self.file = file
        self.name = name
        self.extension = file.filename.split(".")[-1].lower()
        self.chunker = TextChunker(chunk_size, overlap)
        self.text_content, self.file_meta = TextExtractor.extract(file)

    def get_metadata(self) -> dict:
        return {
            "document_name": self.file.filename,
            "user": self.name,
            **self.file_meta
        }

    def build_vectors(self) -> list[dict]:
        chunks = self.chunker.chunk(self.text_content)
        base_metadata = self.get_metadata()
        vectors = []
        for chunk in chunks:
            vectors.append({
                "id": str(uuid.uuid4()),
                "values": get_vector_embeddings(chunk),
                "metadata": {**base_metadata, "text": chunk}
            })
        return vectors

    def prep_pine_code_sdk(self) -> bool:
        vectors = self.build_vectors()
        if upstream_pine_code(vectors):
            with Session(engine) as session:
                session.add(UserMetadataModel(
                    file_name=self.file.filename,
                    user_name=self.name
                ))
                session.commit()
            return True
        return False