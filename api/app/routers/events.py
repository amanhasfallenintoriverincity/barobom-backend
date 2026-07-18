"""Telemetry event ingestion router."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.app.db import get_db
from api.app.models.event import UserEvent
from api.app.models.session import UserSession
from api.app.ai.trace import trace_event

router = APIRouter(prefix="/v1")

VALID_EVENT_TYPES = frozenset([
    "guide_started",
    "step_shown",
    "step_back",
    "step_repeated",
    "new_photo_uploaded",
    "screen_changed",
    "goal_completed",
    "guide_abandoned",
    "user_reported_wrong",
])


class TelemetryPayload(BaseModel):
    anonymous_id: str = Field(..., min_length=20, max_length=64)
    session_id: str = Field(default=None, max_length=36)
    event_type: str = Field(..., min_length=1, max_length=64)
    payload: dict | None = Field(default=None)


class TelemetryResponse(BaseModel):
    session_id: str


@router.post("/events", status_code=201)
async def ingest_event(body: TelemetryPayload, request: Request):
    if body.payload:
        from api.app.safety.redact import redact_text
        def redact_data(data):
            if isinstance(data, dict):
                return {k: redact_data(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [redact_data(v) for v in data]
            elif isinstance(data, str):
                return redact_text(data)
            return data
        body.payload = redact_data(body.payload)
    if body.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown event_type: {body.event_type}")

    # Create or reuse session
    session_id = body.session_id or str(uuid.uuid4())

    # Persist to database (use sync context)
    from api.app.db import SessionLocal
    db = SessionLocal()
    try:
        # Upsert session
        existing = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not existing:
            db.add(UserSession(
                id=session_id,
                anonymous_id=body.anonymous_id,
                user_agent=request.headers.get("user-agent"),
            ))

        db.add(UserEvent(
            session_id=session_id,
            anonymous_id=body.anonymous_id,
            event_type=body.event_type,
            payload=str(body.payload) if body.payload else None,
        ))
        db.commit()
    finally:
        db.close()

    # Trace via Langfuse (fire-and-forget)
    trace_event(body.event_type, body.anonymous_id, body.payload)

    return TelemetryResponse(session_id=session_id)
