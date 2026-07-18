"""Device (kiosk / appliance / screen) model for M2 product identification."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from api.app.db import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # kiosk, appliance, phone, etc.
    brand = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    visual_clues = Column(Text, nullable=True)  # visual features for identification
    usage_context = Column(Text, nullable=True)  # where this device is commonly found
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
