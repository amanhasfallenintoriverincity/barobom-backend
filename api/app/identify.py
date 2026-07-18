"""Device identification router — image → device matching + skill search via ChromaDB."""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.db import SessionLocal
from api.app.models.device import Device
from api.app.skills_store import search_by_device, load_all_skills

router = APIRouter(prefix="/v1")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


class IdentifyRequest(BaseModel):
    image: str = Field(..., min_length=100)
    mime_type: str = Field(default="image/jpeg", max_length=64)


class DeviceResponse(BaseModel):
    id: int
    name: str
    category: str
    brand: str
    model: str
    description: str | None
    confidence: float = Field(default=0.0)


class SkillHit(BaseModel):
    id: str
    title: str
    content: str
    category: str
    brand: str
    model: str
    version: str
    score: float


class IdentifyResponse(BaseModel):
    device: DeviceResponse | None
    skills: list[SkillHit] = []
    raw_analysis: str = ""


def _call_gemini_identify(image_b64: str, mime_type: str) -> str:
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY not configured"

    import httpx
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    prompt = (
        "이 사진 속 기기를 식별해주세요. JSON 형식으로만 답변하세요:\n"
        '{"brand": "브랜드명", "model": "모델명", "category": "kiosk/appliance/phone/remote", '
        '"description": "한 줄 설명"}'
    )

    try:
        response = httpx.post(
            endpoint,
            json={
                "contents": [{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": mime_type, "data": image_b64}},
                    ],
                }],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return text.strip()
    except Exception as e:
        return f"Gemini error: {str(e)}"


def _match_devices_table(analysis_text: str) -> tuple[Device | None, float]:
    """Fallback: match against devices table."""
    try:
        parsed = json.loads(analysis_text)
        brand = parsed.get("brand", "").lower()
        model = parsed.get("model", "").lower()
    except json.JSONDecodeError:
        return None, 0.0

    db = SessionLocal()
    try:
        devices = db.query(Device).all()
        best_match = None
        best_score = 0.0

        for d in devices:
            score = 0.0
            db_brand = d.brand.lower()
            db_model = d.model.lower()

            if model and model in db_model:
                score += 0.6
            elif db_model in model:
                score += 0.5

            if brand and brand in db_brand:
                score += 0.3
            elif db_brand in brand:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = d

        return best_match, best_score
    finally:
        db.close()


@router.post("/identify", response_model=IdentifyResponse)
async def identify_device(body: IdentifyRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured on server")

    raw = _call_gemini_identify(body.image, body.mime_type)

    # 1. Match against devices table
    device, confidence = _match_devices_table(raw)

    # 2. Search ChromaDB for matching skills
    skills = []
    if device:
        chroma_hits = search_by_device(
            brand=device.brand,
            model=device.model,
            category=device.category or "",
            n_results=3,
        )
    else:
        # No device match — try searching with Gemini raw analysis
        chroma_hits = []

    skills = [
        SkillHit(
            id=h["id"],
            title=h["title"],
            content=h["content"],
            category=h.get("category", ""),
            brand=h.get("brand", ""),
            model=h.get("model", ""),
            version=h.get("version", "1.0.0"),
            score=h["score"],
        )
        for h in chroma_hits
    ]

    return IdentifyResponse(
        device=DeviceResponse(
            id=device.id,
            name=device.name,
            category=device.category,
            brand=device.brand,
            model=device.model,
            description=device.description,
            confidence=round(confidence, 2),
        ) if device else None,
        skills=skills,
        raw_analysis=raw,
    )


@router.post("/skills/reload")
def reload_skills():
    """Reload skills from the skills/ directory into ChromaDB."""
    load_all_skills()
    return {"status": "reloaded"}
