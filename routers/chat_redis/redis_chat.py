from fastapi import APIRouter
import redis
router: APIRouter = APIRouter(tags=["Part 2 REDIS"])
r = redis.Redis(host='localhost', port=6379, db=0)
@router.post("/chat")
def chat_with_redis():
    if not r.exists("chat"):
        r.set("chat", "[]")

