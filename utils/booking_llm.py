# helpers for interview booking 

import json
import re
from datetime import date, datetime, time

from google import genai
from sqlmodel import Session

from config import Config
from db.db import engine
from models.booking import UserBookings

client = genai.Client(api_key=Config.GEMINI_API_KEY)
_MODEL = "gemini-flash-latest"


def format_transcript(history: list[dict], message: str) -> str:
    lines: list[str] = []
    for m in history:
        role = (m.get("role") or "user").capitalize()
        content = m.get("content") or ""
        lines.append(f"{role}: {content}")
    lines.append(f"User: {message}")
    return "\n".join(lines)


def is_booking_intent(transcript: str) -> bool:
    prompt = f"""Does this conversation show that the user wants to book, schedule, or set up an interview,
or is providing or correcting details for an interview booking (name, email, date, or time)?

Transcript (oldest first):
{transcript}

Reply with only YES or NO.
"""
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return response.text.strip().upper() == "YES"


def extract_booking_details(transcript: str) -> dict | None:
    today = date.today()
    prompt = f"""Extract interview booking details from the conversation below (use the latest user information).
                    Return ONLY a raw JSON object with keys: name, email, date, time.
- date: string. Prefer YYYY-MM-DD (e.g. 2026-05-24). You may use DD/MM/YYYY, written dates (May 24 2026), etc.
- time: string. Prefer 24-hour HH:MM or HH:MM:SS (e.g. 17:00). You may use 5pm, 5:00 PM, etc.
If any field is missing or not stated, set its value to null.
Do not include any explanation or markdown.

Today's date is {today.isoformat()} (helpful if the user omits the year).

Conversation:
{transcript}"""
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_flexible_time(s: str) -> time:
    s = re.sub(r"\s+", " ", str(s).strip())
    if not s:
        raise ValueError("Empty time")
    s_lower = s.lower()
    s_lower = re.sub(r"(\d)([ap]m)\b", r"\1 \2", s_lower)
    for fmt in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
        "%I %p",
    ):
        try:
            return datetime.strptime(s_lower, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {s!r}")


def _parse_flexible_date(s: str) -> date:
    s = re.sub(r"\s+", " ", str(s).strip())
    if not s:
        raise ValueError("Empty date")
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def save_booking(details: dict) -> UserBookings:
    booking_date = _parse_flexible_date(str(details["date"]))
    t = _parse_flexible_time(str(details["time"]))
    date_col = datetime.combine(booking_date, time.min)
    time_col = datetime.combine(booking_date, t)
    booking = UserBookings(
        Name=details["name"],
        Email=details["email"],
        Date=date_col,
        Time=time_col,
    )
    with Session(engine) as session:
        session.add(booking)
        session.commit()
        session.refresh(booking)
    return booking
