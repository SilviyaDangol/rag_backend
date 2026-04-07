from sqlmodel import SQLModel, Field
from datetime import datetime


class UserBookings(SQLModel, table=True):
    id: int = Field(primary_key=True)
    Name: str = Field(nullable=False)
    Email: str = Field(nullable=False)
    Date: datetime = Field(nullable=False)
    Time: datetime = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)