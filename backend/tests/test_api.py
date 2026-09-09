from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "demo_mode" in body


def test_dataset_endpoint_returns_pilot_cases():
    response = client.get("/api/dataset")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) >= 10


def test_variants_endpoint_returns_501_without_translation_provider():
    response = client.post("/api/variants", json={"english_text": "Hello there"})
    assert response.status_code == 501


def test_variants_endpoint_rejects_empty_text():
    response = client.post("/api/variants", json={"english_text": ""})
    assert response.status_code == 422


def test_evaluate_endpoint_demo_mode():
    payload = {
        "test_case": {
            "id": "VA-001",
            "intent_category": "Benign",
            "intent": "Ask a question",
            "variants": [
                {"form": "english", "text": "Hello", "similarity": 1.0, "verification_status": "verified"},
                {"form": "urdu", "text": "ہیلو", "similarity": 0.9, "verification_status": "verified"},
                {"form": "roman_urdu", "text": "hello", "similarity": 0.9, "verification_status": "verified"},
                {"form": "code_switched", "text": "hello", "similarity": 0.9, "verification_status": "verified"},
            ],
        },
        "models": [{"adapter": "demo", "model_id": "demo-a"}],
    }
    response = client.post("/api/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["demo_mode"] is True
    assert len(body["results"]) == 4
