from sqlmodel import create_engine
from config import Config

DATABASE_URL = Config.DB_URL
engine = create_engine(DATABASE_URL, echo=True)