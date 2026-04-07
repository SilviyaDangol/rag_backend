from fastapi import FastAPI
from sqlmodel import Session, SQLModel
from db.db import engine
from routers.upload_file.ingest import router as ingest_router
from routers.chat_redis.redis_chat import router as redis_chat_router
from routers.book_meetings.booking import router as booking_router

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(ingest_router)
app.include_router(redis_chat_router)
app.include_router(booking_router)
