"""Telemetry endpoint tests."""
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_valid_event():
    payload = {
        "anonymous_id": "a" * 20,
        "event_type": "guide_started",
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 36


def test_ingest_event_with_session_reuse():
    payload = {
        "anonymous_id": "a" * 20,
        "event_type": "guide_started",
    }
    response = client.post("/v1/events", json=payload)
    session_id = response.json()["session_id"]

    payload2 = {
        "anonymous_id": "a" * 20,
        "session_id": session_id,
        "event_type": "step_shown",
    }
    response2 = client.post("/v1/events", json=payload2)
    assert response2.status_code == 201
    assert response2.json()["session_id"] == session_id


def test_ingest_invalid_event_type():
    payload = {
        "anonymous_id": "a" * 20,
        "event_type": "unknown_event",
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 400


def test_ingest_missing_anonymous_id():
    payload = {
        "event_type": "guide_started",
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 422


def test_all_valid_event_types():
    valid_types = [
        "guide_started", "step_shown", "step_back", "step_repeated",
        "new_photo_uploaded", "screen_changed", "goal_completed",
        "guide_abandoned", "user_reported_wrong",
    ]
    for evt in valid_types:
        payload = {"anonymous_id": "a" * 20, "event_type": evt}
        response = client.post("/v1/events", json=payload)
        assert response.status_code == 201, f"Failed for {evt}: {response.text}"


def test_event_with_payload():
    payload = {
        "anonymous_id": "a" * 20,
        "event_type": "step_shown",
        "payload": {"step": 1, "goal": "주문하기"},
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 201
