# SKILL.md 작성 가이드

## 파일 위치
```
skills/{category}/{device-slug}.md
```

예: `skills/kiosk/easy-kiosk-ek-192.md`

## frontmatter (필수)

```yaml
---
device:
  name: "기기 이름 (예: Easy Kiosk EK-192)"
  category: "kiosk | appliance | remote | phone | other"
  brand: "제조사"
  model: "모델명"
  visual_clues:         # Gemini가 이 기기를 식별할 단서
    - "상단 로고"
    - "하단 모델명 표기"
  usage_context: "주로 어디서 사용되는지"
version: "1.0.0"
status: "published"      # draft | published | deprecated
created: "2026-07-18"
---
```

## 본문 작성 규칙

### 구조
1. `## ⚠️ 먼저 확인하세요` — 안전 주의사항
2. `## 화면 구성` — 버튼/영역 위치 설명
3. `## 자주 하는 일` — 목표별 step-by-step 가이드
4. `## 문제 해결` — 흔한 오류와 대처법

### 문장 규칙 (고령층 대상)
- 한 문장에 하나의 행동만
- `-세요` 존댓말 사용
- "누르세요", "확인하세요" 같은 구체적 동사
- 초등학생도 이해할 쉬운 한국어
- 영어/전문용어 지양 (꼭 필요하면 한글 옆에 병기)

### 예시
```markdown
### 커피 주문하기
1. 중앙 화면에서 원하는 메뉴 카테고리를 누르세요
2. 메뉴 목록에서 원하는 음료를 선택하세요
3. "담기" 버튼을 누르세요
```

## 새 Skill 추가 방법

1. `skills/{category}/` 아래에 `.md` 파일 생성
2. frontmatter 정확히 작성
3. GitHub PR 생성 → 팀 리뷰
4. 머지 후 서버에서 `POST /v1/skills/reload` 호출 (또는 서버 재시작)

## 프론트엔드에서 표시될 내용

- `device.name` → 🖥️ 기기 배지
- `h1` → 화면에는 표시 안 함 (관리자용)
- `## 자주 하는 일` → 목표 추천에 활용 (M3+)
- `## 화면 구성` → bbox 생성 힌트로 Gemini에 주입 (M3+)
