from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class UserMetadataModel(SQLModel, table=True):
    id: int = Field(primary_key=True)
    file_name: str = Field(nullable=False)
    updated_at: datetime = Field(nullable=False, default_factory=lambda: datetime.now(tz=timezone.utc))
    user_name: str = Field(nullable=False)
