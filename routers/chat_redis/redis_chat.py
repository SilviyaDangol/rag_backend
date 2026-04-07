from fastapi import APIRouter
import redis
import json
import uuid
from datetime import datetime, timezone
from google import genai
from pinecone_sdk.add_vector import query_top2
from utils.text_embeder import get_vector_embeddings
from config import Config
from utils.booking_utils import is_booking_intent, extract_booking_details, create_booking
from utils.redis_client import get_active_ingest_id

router: APIRouter = APIRouter(tags=["Part 2 REDIS"])
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
client = genai.Client(api_key=Config.GEMINI_API_KEY)


def build_rag_prompt(message: str, context_chunks: list, history: list, now_iso: str) -> str:
    context_text = "\n\n".join(
        match["metadata"].get("text", "")
        for match in context_chunks
        if match.get("metadata")
    )
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        for m in history
    ) if history else "No prior conversation."
    return f"""You are a strict RAG assistant.
               Answer using ONLY the provided Context from the currently ingested document.
               Do not use outside knowledge. Do not guess. Do not hallucinate.
               If the answer is not clearly supported by Context, reply exactly:
               "I don't have enough information in the currently ingested document."
                
                Current datetime (UTC, ISO-8601):
                {now_iso}

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
    now_iso = datetime.now(timezone.utc).isoformat()

    if not session_id:
        session_id = str(uuid.uuid4())

    key = f"chat:{session_id}:messages"
    raw_history = r.lrange(key, -6, -1)
    history = [json.loads(m) for m in raw_history]

    r.rpush(key, json.dumps({"role": "user", "content": message}))

    # Include the latest user turn so booking intent/detail extraction can use full context.
    booking_history = history + [{"role": "user", "content": message}]

    # If the user intends to book a meeting/interview, route to booking flow here.
    if is_booking_intent(message, booking_history):
        details = extract_booking_details(message, booking_history, now_iso=now_iso)
        if not details:
            answer = "I can help book the meeting. Please share your name, email, date (YYYY-MM-DD), and time (HH:MM:SS)."
        else:
            missing = [k for k in ("name", "email", "date", "time") if details.get(k) is None]
            if missing:
                label_map = {"name": "name", "email": "email address", "date": "date (YYYY-MM-DD)", "time": "time (HH:MM:SS)"}
                missing_labels = [label_map[m] for m in missing]
                answer = f"To complete your booking, please share your {', '.join(missing_labels)}."
            else:
                try:
                    reply, booking_id = create_booking(details)
                    answer = f"{reply} (booking_id: {booking_id})"
                except ValueError as e:
                    answer = str(e)

        r.rpush(key, json.dumps({"role": "assistant", "content": answer}))
        return {
            "session_id": session_id,
            "answer": answer,
            "history": history,
        }

    vector_embeddings = get_vector_embeddings(message)
    active_ingest_id = get_active_ingest_id(None)
    if not active_ingest_id:
        answer = "No active ingested document found. Please ingest a document first."
        r.rpush(key, json.dumps({"role": "assistant", "content": answer}))
        return {
            "session_id": session_id,
            "answer": answer,
            "history": history,
        }

    metadata_filter = {"ingest_id": active_ingest_id}
    top_2 = query_top2(vector_embeddings, metadata_filter=metadata_filter)
    if not top_2:
        answer = "I don't have enough information in the currently ingested document."
        r.rpush(key, json.dumps({"role": "assistant", "content": answer}))
        return {
            "session_id": session_id,
            "answer": answer,
            "history": history,
        }

    # Inject request-time UTC datetime into prompt for grounding.
    prompt = build_rag_prompt(message, top_2, history, now_iso=now_iso)
    answer = call_gemini(prompt)

    r.rpush(key, json.dumps({"role": "assistant", "content": answer}))

    return {
        "session_id": session_id,
        "answer": answer,
        "history": history,
    }