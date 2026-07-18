"""User event model."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from api.app.db import Base


class UserEvent(Base):
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    anonymous_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
