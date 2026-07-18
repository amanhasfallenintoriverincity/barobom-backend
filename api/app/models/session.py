"""User session model."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text
from api.app.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True)
    anonymous_id = Column(String(64), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
