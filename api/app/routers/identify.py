"""Device identification router — image → device matching + Google Search grounding fallback."""
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


class Citation(BaseModel):
    url: str
    title: str
    snippet: str = ""


class IdentifyResponse(BaseModel):
    device: DeviceResponse | None
    skills: list[SkillHit] = []
    raw_analysis: str = ""
    search_used: bool = False
    citations: list[Citation] = []


def _call_gemini_identify(image_b64: str, mime_type: str) -> str:
    """Basic image -> device identification via gemini generateContent."""
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY not configured"

    import httpx
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    prompt = (
        '\uc774 \uc0ac\uc9c4 \uc18d \uae30\uae30\ub97c \uc2dd\ubcc4\ud574\uc8fc\uc138\uc694. JSON \ud615\uc2dd\uc73c\ub85c\ub9cc \ub2f5\ubcc0\ud558\uc138\uc694:\n'
        '{"brand": "\ube0c\ub79c\ub4dc\uba85", "model": "\ubaa8\ub378\uba85", "category": "kiosk/appliance/phone/remote", '
        '"description": "\ud55c \uc904 \uc124\uba85"}'
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
            timeout=120.0,
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


def _call_google_search_identify(image_b64: str, mime_type: str, raw_analysis: str) -> dict:
    """Google Search grounded identification via Interactions API."""
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}

    import httpx
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/interactions"
        f"?key={GEMINI_API_KEY}"
    )

    prompt = (
        f"Initial device analysis: {raw_analysis}. "
        "Search Google to identify this device. "
        "Reply ONLY with JSON: "
        '{"brand":"","model":"","category":"","description":"","search_used":true}'
    )

    try:
        response = httpx.post(
            endpoint,
            json={
                "model": GEMINI_MODEL,
                "input": prompt,
                "tools": [{"type": "google_search"}],
            },
            timeout=120.0,
        )

        if response.status_code == 429:
            return {"error": "rate_limited", "text": raw_analysis, "citations": []}

        response.raise_for_status()
        data = response.json()

        text = ""
        citations = []
        for step in data.get("steps", []):
            if step["type"] == "model_output":
                for block in step.get("content", []):
                    if block["type"] == "text":
                        text = block["text"]
                        for ann in block.get("annotations", []):
                            if ann["type"] == "url_citation":
                                start = ann.get("start_index", 0)
                                end = ann.get("end_index", 0)
                                citations.append({
                                    "url": ann.get("url", ""),
                                    "title": ann.get("title", ""),
                                    "snippet": text[start:end],
                                })

        device_info = {}
        try:
            device_info = json.loads(text)
        except json.JSONDecodeError:
            device_info = {"brand": "", "model": "", "category": "", "description": text[:200]}

        return {"text": text, "citations": citations, "device_info": device_info}

    except Exception as e:
        return {"error": str(e), "text": raw_analysis, "citations": []}


def _match_devices_table(analysis_text: str) -> tuple:
    """Match analysis text against devices table. Returns (Device|None, float)."""
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
    from api.app.safety.redact import redact_image
    body.image = redact_image(body.image)
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured on server")

    raw = _call_gemini_identify(body.image, body.mime_type)

    device, confidence = _match_devices_table(raw)

    skills = []
    if device:
        chroma_hits = search_by_device(
            brand=device.brand,
            model=device.model,
            category=device.category or "",
            n_results=3,
        )
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

    search_used = False
    citations = []
    if device is None and not raw.startswith("Gemini error"):
        grounded = _call_google_search_identify(body.image, body.mime_type, raw)
        if "error" not in grounded:
            search_used = True
            citations = [
                Citation(url=c["url"], title=c["title"], snippet=c["snippet"])
                for c in grounded.get("citations", [])
            ]
            dinfo = grounded.get("device_info", {})
            if dinfo.get("brand") or dinfo.get("model"):
                device = Device(
                    id=0,
                    name=f"{dinfo.get('brand', '')} {dinfo.get('model', '')}".strip() or "\ubbf8\ud655\uc778 \uae30\uae30",
                    category=dinfo.get("category", "unknown"),
                    brand=dinfo.get("brand", "\ubbf8\ud655\uc778"),
                    model=dinfo.get("model", "\ubbf8\ud655\uc778"),
                    description=dinfo.get("description", raw[:100]),
                )
                confidence = 0.5
                raw = grounded.get("text", raw)

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
        search_used=search_used,
        citations=citations,
    )


@router.post("/skills/reload")
def reload_skills():
    """Reload skills from the skills/ directory into ChromaDB."""
    load_all_skills()
    return {"status": "reloaded"}
