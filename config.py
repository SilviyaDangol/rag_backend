from dotenv import load_dotenv
load_dotenv()
import os

class Config:
    PINECONE_DEFAULT_API = os.getenv('PINECONE_DEFAULT_API')
    PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')
    DB_URL = os.getenv('DATABASE_URL')