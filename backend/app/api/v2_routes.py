"""VeriAudit v2 API: serves real research outputs only.

Every payload carries `"kind": "real"`; the v1 demo endpoints (`/api/evaluate`, `/api/variants`)
are unchanged and remain labelled as demo by `demo_mode`.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.veriaudit_x.schema import json_schema
from app.veriaudit_x.validation import ValidationConfig, validate_file

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = ROOT / "results" / "v2" / "dashboard.json"
PAIRED_CSV = ROOT / "results" / "v1_reconstruction" / "paired_tests.csv"

router = APIRouter(prefix="/v2", tags=["v2 (real results)"])


def _dashboard() -> dict:
    if not DASHBOARD.exists():
        raise HTTPException(status_code=404, detail="results/v2/dashboard.json not built; run research/platform/export_dashboard_data.py")
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


@router.get("/summary")
def summary() -> dict:
    return {"kind": "real", **_dashboard()}


@router.get("/status")
def status() -> dict:
    return {"kind": "real", "status": _dashboard()["status"]}


@router.get("/v1-reconstruction")
def v1_reconstruction() -> dict:
    return {"kind": "real", **_dashboard()["v1"]}


@router.get("/v1-reconstruction/paired_tests.csv")
def v1_paired_csv() -> FileResponse:
    if not PAIRED_CSV.exists():
        raise HTTPException(status_code=404, detail="reconstruction outputs missing")
    return FileResponse(PAIRED_CSV, media_type="text/csv", filename="veriaudit_v1_paired_tests.csv")


@router.get("/dataset/schema")
def dataset_schema() -> dict:
    return json_schema()


class ValidateRequest(BaseModel):
    jsonl: str = Field(min_length=1, description="VeriAudit-X records, one JSON object per line")
    require_all_languages: bool = True


@router.post("/dataset/validate")
def dataset_validate(payload: ValidateRequest) -> dict:
    if len(payload.jsonl.encode("utf-8")) > get_settings().max_request_bytes * 10:
        raise HTTPException(status_code=413, detail="Request too large")
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False) as f:
        f.write(payload.jsonl)
        path = Path(f.name)
    try:
        report = validate_file(path, ValidationConfig(require_all_languages=payload.require_all_languages))
    finally:
        path.unlink(missing_ok=True)
    return {
        "valid_records": len(report.records),
        "errors": [vars(i) for i in report.errors],
        "warnings": [vars(i) for i in report.warnings],
        "ok": report.ok,
    }
