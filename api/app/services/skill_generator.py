"""Skill draft generator — aggregates observations into SKILL.md drafts."""
import os
from api.app.db import SessionLocal
from api.app.models.observation import Observation
from api.app.models.device import Device
from api.app.models.device_skill import DeviceSkill

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


def generate_skill_draft(device_id: int) -> dict | None:
    """Aggregate unprocessed observations for a device and generate a SKILL.md draft via Gemini."""
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": "device not found"}

        obs_list = (
            db.query(Observation)
            .filter(
                Observation.device_id == device_id,
                Observation.processed == False,
            )
            .order_by(Observation.created_at.asc())
            .limit(20)
            .all()
        )

        if len(obs_list) < 3:
            return {"error": "insufficient observations", "count": len(obs_list)}

        # Build observation summary
        obs_text = "\n".join(
            f"- [{o.observation_type}] step={o.step_index} {o.description or ""}"
            for o in obs_list
        )

        # Get existing published skill as reference
        existing = (
            db.query(DeviceSkill)
            .filter(
                DeviceSkill.device_id == device_id,
                DeviceSkill.status == "published",
            )
            .first()
        )

        existing_text = existing.content if existing else "(신규 기기 — 기존 가이드 없음)"

        # Call Gemini to generate draft
        prompt = f"""당신은 디지털 기기 사용 가이드 작성 전문가입니다.

기기 정보: {device.name} ({device.brand} {device.model})
카테고리: {device.category}
사용 맥락: {device.usage_context or "일반 가정"}

기존 가이드:
{existing_text[:1000]}

사용자 피드백 (관찰):
{obs_text}

위 피드백을 바탕으로 기존 가이드를 개선한 새 SKILL.md 초안을 작성하세요.
YAML frontmatter 없이 마크다운 본문만 작성하세요.
# 화면 구성, # 지원 목표, # 주의사항 섹션을 반드시 포함하세요.
한국어로 작성하세요."""

        import httpx

        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
            },
            timeout=30.0,
        )
        if resp.status_code == 429:
            return {"error": "rate_limited", "message": "Gemini API quota exceeded"}
        resp.raise_for_status()
        data = resp.json()
        draft = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Mark observations as processed
        for o in obs_list:
            o.processed = True
        db.commit()

        # Determine next version
        if existing:
            try:
                major = int(existing.version.split(".")[0])
            except (ValueError, IndexError):
                major = 0
            next_ver = f"{major + 1}.0.0"
        else:
            next_ver = "1.0.0"

        # Save as draft DeviceSkill
        skill = DeviceSkill(
            device_id=device_id,
            title=f"{device.name} 가이드 (자동 생성)",
            content=draft,
            version=next_ver,
            status="draft",
        )
        db.add(skill)
        db.commit()

        return {
            "skill_id": skill.id,
            "status": "draft",
            "observation_count": len(obs_list),
        }
    finally:
        db.close()

# 429 handler patch: return user-friendly error
# (append after the raise_for_status block in generate_skill_draft)
