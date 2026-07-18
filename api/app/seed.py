"""Seed data for known devices."""
from api.app.db import SessionLocal, init_db
from api.app.models.device import Device
from api.app.models.device_skill import DeviceSkill

SEED_DEVICES = [
    {
        "name": "Easy Kiosk EK-192",
        "category": "kiosk",
        "brand": "이지포스/KICC",
        "model": "EK-192",
        "description": "무인 주문·결제 키오스크. 메가MGC커피 등 프랜차이즈 매장에서 사용.",
        "visual_clues": "화면 상단 '메가엠지씨커피' 로고, 하단 'Easy Kiosk EK-192' 표기, 좌측 '애플페이는 이쪽' 스티커, 카드 결제 모듈",
        "usage_context": "프랜차이즈 커피숍 (메가MGC커피), 패스트푸드 매장",
    },
    {
        "name": "LG 트롬 세탁기",
        "category": "appliance",
        "brand": "LG",
        "model": "TROMM",
        "description": "LG 트롬 드럼 세탁기. 다이얼식 코스 선택 + 터치 디스플레이.",
        "visual_clues": "원형 다이얼, LG 로고, '트롬' 배지, 코스 이름 (표준세탁, 탈수, 헹굼 등)",
        "usage_context": "가정용 세탁실",
    },
    {
        "name": "삼성 에어컨 리모컨",
        "category": "appliance",
        "brand": "삼성",
        "model": "무풍",
        "description": "삼성 무풍 에어컨 리모컨. LCD 디스플레이 + 다수 버튼.",
        "visual_clues": "상단 LCD 화면, '무풍' 버튼, 온도 ↑↓, 바람 세기, 모드 선택",
        "usage_context": "가정용 에어컨",
    },
    {
        "name": "보일러 실내 온도조절기",
        "category": "appliance",
        "brand": "귀뚜라미",
        "model": "CTR-5500",
        "description": "귀뚜라미 보일러 실내 온도조절기. 난방·온수·외출 모드.",
        "visual_clues": "LCD 디스플레이, '난방'·'온수'·'외출' 버튼, 온도 숫자",
        "usage_context": "가정용 보일러",
    },
]

SEED_SKILLS = [
    {
        "device_index": 0,
        "title": "메가MGC커피 키오스크로 주문하기",
        "content": """# 메가MGC커피 키오스크로 주문하기 (EK-192)

## 기기 정보
- 기종: Easy Kiosk EK-192 (이지포스/KICC)
- 매장: 메가MGC커피

## 사용 가능한 목표
1. 커피 주문하기
2. 결제하기 (카드/애플페이)
3. 포인트 적립하기

## 화면 구성
- 상단: 메가MGC커피 로고
- 중앙: 메뉴 선택 영역
- 하단: 장바구니 + 결제 버튼
- 좌측 하단: 애플페이 결제 단말기

## 주의사항
- 결제 전에 장바구니 내용을 꼭 확인하세요
- 애플페이는 왼쪽 별도 단말기로 결제합니다
- 영수증은 자동으로 출력됩니다""",
    },
]


def seed():
    """Insert seed data if the devices table is empty."""
    init_db()
    db = SessionLocal()
    try:
        if db.query(Device).count() > 0:
            print("Seed data already exists, skipping.")
            return

        for d in SEED_DEVICES:
            db.add(Device(**d))
        db.flush()

        for s in SEED_SKILLS:
            device = db.query(Device).all()[s["device_index"]]
            db.add(DeviceSkill(
                device_id=device.id,
                title=s["title"],
                content=s["content"],
            ))

        db.commit()
        print(f"Seeded {len(SEED_DEVICES)} devices and {len(SEED_SKILLS)} skills.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
