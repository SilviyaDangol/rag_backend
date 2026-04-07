from fastapi import APIRouter
import redis
import json
import uuid
from google import genai
from pinecone_sdk.add_vector import query_top2
from utils.text_embeder import get_vector_embeddings
from config import Config

router: APIRouter = APIRouter(tags=["Part 2 REDIS"])
r = redis.Redis(host="localhost", port=6379, db=0)
client = genai.Client(api_key=Config.GEMINI_API_KEY)


def build_rag_prompt(message: str, context_chunks: list, history: list) -> str:
    context_text = "\n\n".join(
        match["metadata"].get("text", "")
        for match in context_chunks
        if match.get("metadata")
    )
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        for m in history
    ) if history else "No prior conversation."
    return f"""Answer the question using ONLY the context provided below.
               If the answer is not in the context, say you don't have enough information.
                
                Context:
                {context_text}
                
                Chat History:
                {history_text}
                
                Question: {message}
                
                Answer:"""

def call_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )
    return response.text.strip()


@router.post("/chat")
def chat_with_redis(message: str, session_id: str | None = None):
    if not session_id:
        session_id = str(uuid.uuid4())

    key = f"chat:{session_id}:messages"
    raw_history = r.lrange(key, -6, -1)
    history = [json.loads(m) for m in raw_history]

    r.rpush(key, json.dumps({"role": "user", "content": message}))

    vector_embeddings = get_vector_embeddings(message)
    top_2 = query_top2(vector_embeddings)

    prompt = build_rag_prompt(message, top_2, history)
    answer = call_gemini(prompt)

    r.rpush(key, json.dumps({"role": "assistant", "content": answer}))

    return {
        "session_id": session_id,
        "answer": answer,
        "history": history,
    }