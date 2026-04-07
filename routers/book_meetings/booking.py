from fastapi import APIRouter, HTTPException
from google import genai
from sqlmodel import Session
from models.booking import UserBookings
from db.db import engine
from config import Config
from datetime import datetime
import json

router = APIRouter(prefix="/booking", tags=["Part 3 BOOKING"])
client = genai.Client(api_key=Config.GEMINI_API_KEY)


def is_booking_intent(message: str) -> bool:
    prompt = f"""Does this message express an intent to book, schedule, or set up an interview?
                Reply with only YES or NO.
                Message: {message}
                """
    response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
    return response.text.strip().upper() == "YES"


def extract_booking_details(message: str) -> dict | None:
    prompt = f"""Extract booking details from the message below.
                Return ONLY a raw JSON object with keys: name, email, date, time.
                date format must be: YYYY-MM-DD
                time format must be: HH:MM:SS
                If any field is missing, set its value to null.
                Do not include any explanation or markdown.

                Message: {message}"""
    response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
    try:
        return json.loads(response.text.strip())
    except json.JSONDecodeError:
        return None

@router.post("/chat")
def booking_chat(message: str):
    if not is_booking_intent(message):
        return {"reply": "I can help you book an interview. Please provide your name, email, date, and time."}
    details = extract_booking_details(message)
    if not details:
        raise HTTPException(status_code=422, detail="Could not extract booking details from the message.")
    missing = [k for k, v in details.items() if v is None]
    if missing:
        return {"reply": f"Please provide the following missing details: {', '.join(missing)}"}
    booking = UserBookings(
        Name=details["name"],
        Email=details["email"],
        Date=datetime.strptime(details["date"], "%Y-%m-%d"),
        Time=datetime.strptime(details["time"], "%H:%M:%S"),
    )
    with Session(engine) as session:
        session.add(booking)
        session.commit()
        session.refresh(booking)
    return {
        "reply": f"Great, {booking.Name}! Your interview is booked for {booking.Date.date()} at {booking.Time.time()}.",
        "booking_id": booking.id
    }