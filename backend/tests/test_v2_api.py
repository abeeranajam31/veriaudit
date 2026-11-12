from fastapi.testclient import TestClient
from veriaudit_x_helpers import FIXTURE_FILE

from app.main import app

client = TestClient(app)


def test_v2_summary_is_real_and_reproduced():
    r = client.get("/api/v2/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "real"
    assert body["v1"]["verification"]["matched"] == body["v1"]["verification"]["checks"] == 191
    assert any(s["state"] == "blocked" for s in body["status"])


def test_v2_reconstruction_and_csv_export():
    r = client.get("/api/v2/v1-reconstruction")
    assert r.status_code == 200 and len(r.json()["comparisons"]) == 6
    csv = client.get("/api/v2/v1-reconstruction/paired_tests.csv")
    assert csv.status_code == 200 and csv.text.startswith("analysis,")


def test_v2_schema_and_validate_endpoint():
    assert client.get("/api/v2/dataset/schema").json()["title"].startswith("VeriAudit-X")
    good = client.post("/api/v2/dataset/validate", json={"jsonl": FIXTURE_FILE.read_text(encoding="utf-8")}).json()
    assert good["ok"] and good["valid_records"] == 28
    bad = client.post("/api/v2/dataset/validate", json={"jsonl": "{not json}\n"}).json()
    assert not bad["ok"] and bad["errors"][0]["code"] == "invalid_json"


def test_v1_demo_endpoints_unchanged():
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.post("/api/variants", json={"english_text": "Hello"}).status_code == 501
