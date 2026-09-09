from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.evaluation.equiv_engine import EquivEngine
from app.evaluation.gap_evaluator import GapEvaluator
from app.models.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
)
from app.reports.evidence_report import build_evidence_report
from app.utils.dataset_loader import load_dataset

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode}


@router.get("/dataset")
def get_dataset() -> list[dict]:
    try:
        cases = load_dataset()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [c.model_dump() for c in cases]


@router.post("/variants", response_model=GenerateVariantsResponse)
def generate_variants(payload: GenerateVariantsRequest) -> GenerateVariantsResponse:
    if len(payload.english_text.encode("utf-8")) > settings.max_request_bytes:
        raise HTTPException(status_code=413, detail="Request too large")
    engine = EquivEngine()
    try:
        return engine.generate_variants(payload.english_text)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest) -> EvaluateResponse:
    evaluator = GapEvaluator()
    results = evaluator.evaluate(payload.test_case, payload.models)
    return EvaluateResponse(results=results, demo_mode=settings.demo_mode)


@router.post("/evaluate/report")
def evaluate_report(payload: EvaluateRequest) -> Response:
    evaluator = GapEvaluator()
    results = evaluator.evaluate(payload.test_case, payload.models)
    audit_id = f"VA-AUDIT-{uuid.uuid4().hex[:8].upper()}"
    pdf_bytes = build_evidence_report(audit_id, [payload.test_case], results)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{audit_id}.pdf"'},
    )
