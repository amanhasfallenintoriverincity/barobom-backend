"""Rule-based skill evaluator — validates SKILL.md drafts before publishing."""
import re


def evaluate_skill(content: str) -> dict:
    """Run rule-based checks on a SKILL.md draft. Returns score 0-100 + failures."""
    failures = []
    score = 100

    # Must have required sections
    required_sections = ["화면 구성", "지원 목표", "주의사항"]
    for section in required_sections:
        if section not in content:
            failures.append(f"missing_section:{section}")
            score -= 20

    # Must be Korean-heavy
    korean_chars = len(re.findall(r"[가-힣]", content))
    if korean_chars < 50:
        failures.append("too_little_korean")
        score -= 15

    # No dangerous instructions
    dangerous = ["전원을 뽑으", "분해", "잠금 해제", "비밀번호를 입력"]
    for d in dangerous:
        if d in content:
            failures.append(f"dangerous_instruction:{d}")
            score -= 25

    # Must have at least 200 chars
    if len(content) < 200:
        failures.append("too_short")
        score -= 20

    # Bbox coordinates check (if present) — must be 0-100
    bbox_pattern = r"\"box\"\s*:\s*\{[^}]*\"x\"\s*:\s*(-?\d+)"
    for m in re.finditer(bbox_pattern, content):
        if int(m.group(1)) < 0 or int(m.group(1)) > 100:
            failures.append("invalid_bbox")
            score -= 10
            break

    passed = len(failures) == 0
    return {"passed": passed, "score": max(0, score), "failures": failures}
