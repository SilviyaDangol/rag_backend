from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
import json
import uuid
from google import genai
from pinecone_sdk.add_vector import query_top2
from utils.text_embeder import get_vector_embeddings
from utils.redis_client import r, get_active_ingest_id
from utils.booking_llm import (
    format_transcript,
    is_booking_intent,
    extract_booking_details,
    save_booking,
)
from config import Config

router: APIRouter = APIRouter(tags=["Part 2 REDIS"])
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


def _chat_response(
    *,
    session_id: str,
    answer: str,
    history: list,
    booking_id: int | None = None,
) -> dict:
    out = {
        "session_id": session_id,
        "answer": answer,
        "history": history,
    }
    if booking_id is not None:
        out["booking_id"] = booking_id
    return out


_CHAT_MESSAGE_DESCRIPTION = (
    "**RAG:** ask about content from ingested documents. "
    "**Interview booking:** include name, email, when (date), and time. "
)


@router.post("/chat")
def chat_with_redis(
    message: Annotated[
        str,
        Query(
            ...,
            description=_CHAT_MESSAGE_DESCRIPTION,
            examples={
                "rag": {
                    "summary": "Document question",
                    "value": "What are the main topics in my uploaded file?",
                },
                "booking_iso": {
                    "summary": "Booking (ISO date + 24h time)",
                    "value": "Book interview for silviya dangolsilviya@gmail.com on 2026-05-24 at 17:00",
                },
            },
        ),
    ],
    session_id: Annotated[
        str | None,
        Query(description="Optional but reuse to continue the same Redis-backed conversation."),
    ] = None,
    user_name: Annotated[
        str | None,
        Query(
            description=(
                "Use same value as the name field used when ingesting. "
                "When set, retrieval uses only chunks from that user's latest successful uploads"
            ),
        ),
    ] = None,
):
    if not session_id:
        session_id = str(uuid.uuid4())

    key = f"chat:{session_id}:messages"
    raw_history = r.lrange(key, -6, -1)
    history = [json.loads(m) for m in raw_history]

    r.rpush(key, json.dumps({"role": "user", "content": message}))

    transcript = format_transcript(history, message)

    if is_booking_intent(transcript):
        details = extract_booking_details(transcript)
        if not details:
            raise HTTPException(
                status_code=422,
                detail="Could not extract booking details from the conversation.",
            )
        missing = [k for k, v in details.items() if v is None]
        if missing:
            answer = f"Please provide the following missing details: {', '.join(missing)}"
            r.rpush(key, json.dumps({"role": "assistant", "content": answer}))
            return _chat_response(session_id=session_id, answer=answer, history=history)

        try:
            booking = save_booking(details)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid booking date or time: {exc}",
            ) from exc
        answer = (
            f"Great, {booking.Name}! Your interview is booked for {booking.Date.date().isoformat()} "
            f"at {booking.Time.time().strftime('%H:%M:%S')}."
        )
        r.rpush(key, json.dumps({"role": "assistant", "content": answer}))
        return _chat_response(
            session_id=session_id,
            answer=answer,
            history=history,
            booking_id=booking.id,
        )

    vector_embeddings = get_vector_embeddings(message)
    pinecone_filter = None
    uname = (user_name or "").strip()
    if uname:
        active = get_active_ingest_id(uname)
        if active:
            pinecone_filter = {"ingest_id": {"$eq": active}}
    top_2 = query_top2(vector_embeddings, metadata_filter=pinecone_filter)

    prompt = build_rag_prompt(message, top_2, history)
    answer = call_gemini(prompt)

    r.rpush(key, json.dumps({"role": "assistant", "content": answer}))

    return _chat_response(session_id=session_id, answer=answer, history=history)
