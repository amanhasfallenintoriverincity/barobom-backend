"""Observation model — user behaviour / feedback captured from device sessions."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, ForeignKey
from api.app.db import Base


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=True)
    observation_type = Column(String(64), nullable=False)  # click_path, hesitation, error, voice, etc.
    step_index = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)  # JSON blob
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
