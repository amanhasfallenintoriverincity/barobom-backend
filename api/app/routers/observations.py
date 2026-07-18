"""Observation ingestion router."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from api.app.db import SessionLocal
from api.app.models.observation import Observation

router = APIRouter(prefix="/v1")


class ObservationPayload(BaseModel):
    device_id: int = Field(..., ge=1)
    session_id: str = Field(..., min_length=1, max_length=36)
    observation_type: str = Field(..., pattern=r"^(wrong_step|missing_step|correct_step)$")
    description: str | None = None
    step_index: int | None = None


@router.post("/observations", status_code=201)
def ingest_observation(body: ObservationPayload):
    db = SessionLocal()
    try:
        obs = Observation(
            device_id=body.device_id,
            session_id=body.session_id,
            observation_type=body.observation_type,
            description=body.description,
            step_index=body.step_index,
        )
        db.add(obs)
        db.commit()
        count = db.query(Observation).filter(
            Observation.device_id == body.device_id,
            Observation.observation_type == body.observation_type,
            Observation.processed == False,
        ).count()
        return {"id": obs.id, "unprocessed_count": count}
    finally:
        db.close()


@router.get("/observations/pending")
def pending_observations(device_id: int = None):
    """List unprocessed observations, optionally filtered by device."""
    db = SessionLocal()
    try:
        q = db.query(Observation).filter(Observation.processed == False)
        if device_id:
            q = q.filter(Observation.device_id == device_id)
        return [
            {
                "id": o.id,
                "device_id": o.device_id,
                "type": o.observation_type,
                "description": o.description,
                "step_index": o.step_index,
                "created_at": o.created_at.isoformat(),
            }
            for o in q.order_by(Observation.created_at.desc()).limit(50).all()
        ]
    finally:
        db.close()
