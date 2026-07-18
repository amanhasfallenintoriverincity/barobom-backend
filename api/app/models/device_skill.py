"""SKILL.md lookup model — connects devices to usage guides."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from api.app.db import Base


class DeviceSkill(Base):
    __tablename__ = "device_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)  # SKILL.md content
    version = Column(String(16), default="1.0.0")
    status = Column(String(32), default="published")  # draft, published, deprecated
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
