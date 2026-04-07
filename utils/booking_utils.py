import json
from datetime import datetime

from google import genai
from sqlmodel import Session

from config import Config
from db.db import engine
from models.booking import UserBookings

client = genai.Client(api_key=Config.GEMINI_API_KEY)


def is_booking_intent(message: str, history: list[dict]) -> bool:
    history_text = "\n".join(
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
        for m in history
    ) if history else "No prior conversation."
    prompt = f"""Decide whether the user is trying to book, schedule, or set up an interview.
                Use both the latest message and chat history for context.
                Reply with only YES or NO.

                Chat History:
                {history_text}

                Latest Message: {message}
                """
    response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
    return response.text.strip().upper() == "YES"


def extract_booking_details(message: str, history: list[dict], now_iso: str) -> dict | None:
    history_text = "\n".join(
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
        for m in history
    ) if history else "No prior conversation."
    prompt = f"""Extract booking details from the message below.
                Return ONLY a raw JSON object with keys: name, email, date, time.
                date format must be: YYYY-MM-DD
                time format must be: HH:MM:SS
                If any field is missing, set its value to null.
                Do not include any explanation or markdown.
                Today's datetime in UTC (ISO-8601): {now_iso}
                Use this as the current reference date when resolving relative phrases
                like "today", "tomorrow", "next week", or ambiguous dates.
                Do not pick a past date unless the user explicitly asked for a past date.
                If a detail (name, email, date, or time) is missing in the latest message,
                search the provided Chat History to see if it was mentioned earlier.

                Chat History:
                {history_text}

                Latest Message: {message}"""
    response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
    try:
        return json.loads(response.text.strip())
    except json.JSONDecodeError:
        return None


def create_booking(details: dict) -> tuple[str, int]:
    """
    Persist a booking to DB from extracted details.
    Returns (reply_text, booking_id).
    Raises ValueError if required fields are missing/invalid.
    """
    required = ("name", "email", "date", "time")
    missing = [k for k in required if details.get(k) in (None, "", [])]
    if missing:
        raise ValueError(f"Missing booking details: {', '.join(missing)}")

    try:
        date_obj = datetime.strptime(details["date"], "%Y-%m-%d")
    except Exception as e:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD.") from e

    try:
        time_obj = datetime.strptime(details["time"], "%H:%M:%S").time()
    except Exception as e:
        raise ValueError("Invalid time format. Expected HH:MM:SS.") from e

    # Prevent accidental bookings in the past caused by ambiguous date extraction.
    if date_obj.date() < datetime.utcnow().date():
        raise ValueError(
            f"The provided date {date_obj.date()} is in the past. "
            "Please provide a future date in YYYY-MM-DD."
        )

    booking = UserBookings(
        Name=str(details["name"]).strip(),
        Email=str(details["email"]).strip(),
        Date=date_obj,
        Time=time_obj,
    )

    with Session(engine) as session:
        session.add(booking)
        session.commit()
        session.refresh(booking)

    reply = (
        f"Great, {booking.Name}! Your interview is booked for "
        f"{booking.Date.date()} at {booking.Time}."
    )
    return reply, booking.id

