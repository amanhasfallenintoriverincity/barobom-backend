"""Skill management router — generation + publishing."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from api.app.db import SessionLocal
from api.app.models.device_skill import DeviceSkill
from api.app.services.skill_generator import generate_skill_draft
from api.app.services.skill_evaluator import evaluate_skill

router = APIRouter(prefix="/v1")


class GenerateRequest(BaseModel):
    device_id: int = Field(..., ge=1)


@router.post("/skills/generate")
def generate_skill(body: GenerateRequest):
    result = generate_skill_draft(body.device_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/skills/{skill_id}/evaluate")
def evaluate_skill_endpoint(skill_id: int):
    db = SessionLocal()
    try:
        skill = db.query(DeviceSkill).filter(DeviceSkill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="skill not found")
        result = evaluate_skill(skill.content)
        return {"skill_id": skill_id, **result}
    finally:
        db.close()


@router.post("/skills/{skill_id}/publish")
def publish_skill(skill_id: int):
    db = SessionLocal()
    try:
        skill = db.query(DeviceSkill).filter(DeviceSkill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="skill not found")
        if skill.status != "draft":
            raise HTTPException(
                status_code=400,
                detail=f"cannot publish skill in status: {skill.status}",
            )
        ev = evaluate_skill(skill.content)
        if not ev["passed"]:
            raise HTTPException(
                status_code=400, detail={"evaluation_failed": ev}
            )
        # Deprecate current published version
        db.query(DeviceSkill).filter(
            DeviceSkill.device_id == skill.device_id,
            DeviceSkill.status == "published",
        ).update({"status": "deprecated"})
        skill.status = "published"
        db.commit()
        return {"skill_id": skill_id, "status": "published", "evaluation": ev}
    finally:
        db.close()


@router.post("/skills/{skill_id}/rollback")
def rollback_skill(skill_id: int):
    db = SessionLocal()
    try:
        skill = db.query(DeviceSkill).filter(DeviceSkill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="skill not found")
        if skill.status != "published":
            raise HTTPException(
                status_code=400, detail="only published skills can be rolled back"
            )
        # Find previous published version
        prev = (
            db.query(DeviceSkill)
            .filter(
                DeviceSkill.device_id == skill.device_id,
                DeviceSkill.status == "deprecated",
                DeviceSkill.id != skill_id,
            )
            .order_by(DeviceSkill.updated_at.desc())
            .first()
        )
        if prev:
            prev.status = "published"
        skill.status = "deprecated"
        db.commit()
        return {"rolled_back": skill_id, "restored": prev.id if prev else None}
    finally:
        db.close()


@router.get("/skills")
def list_skills(
    status: str = Query(None),
    device_id: int = Query(None),
):
    db = SessionLocal()
    try:
        q = db.query(DeviceSkill)
        if status:
            q = q.filter(DeviceSkill.status == status)
        if device_id:
            q = q.filter(DeviceSkill.device_id == device_id)
        return [
            {
                "id": s.id,
                "device_id": s.device_id,
                "title": s.title,
                "version": s.version,
                "status": s.status,
                "updated_at": s.updated_at.isoformat(),
            }
            for s in q.order_by(DeviceSkill.updated_at.desc()).limit(20).all()
        ]
    finally:
        db.close()
