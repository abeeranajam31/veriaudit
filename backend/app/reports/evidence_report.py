"""EvidenceReport — generates a downloadable PDF audit report via ReportLab.

This report documents a technical evaluation. It intentionally avoids any
claim of legal or regulatory compliance.
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.evaluation.clsg import average_clsg
from app.models.schemas import LinguisticForm, ModelLanguageResult, TestCase

DISCLAIMER = (
    "This report provides technical evaluation evidence that may support AI risk "
    "assessment and governance workflows. It is not legal advice or a certification "
    "of regulatory compliance."
)


def build_evidence_report(
    audit_id: str,
    test_cases: list[TestCase],
    results: list[ModelLanguageResult],
    dataset_version: str = "VERIAUDIT-500 pilot",
    reference_form: LinguisticForm = LinguisticForm.english,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("VATitle", parent=styles["Title"], textColor=colors.HexColor("#0f6b52"))
    small = ParagraphStyle("VASmall", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    story = [
        Paragraph("VERIAUDIT", title_style),
        Paragraph("Cross-Lingual AI Safety Evidence Report", styles["Heading2"]),
        Spacer(1, 0.15 * inch),
        Paragraph(f"Audit ID: {audit_id}", styles["Normal"]),
        Paragraph(f"Date: {date.today().isoformat()}", styles["Normal"]),
        Paragraph(f"Dataset / version: {dataset_version}", styles["Normal"]),
        Paragraph(
            "Models: " + ", ".join(sorted({r.model_id for r in results})),
            styles["Normal"],
        ),
        Paragraph(
            "Languages: " + ", ".join(sorted({r.form.value for r in results})),
            styles["Normal"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Methodology", styles["Heading3"]),
        Paragraph(
            "Intent-level test cases were expressed as semantically equivalent variants "
            "across languages (EquivEngine), evaluated under identical conditions "
            "(GapEvaluator), and scored across refusal consistency, instruction following, "
            "and safety. See veriaudit.dev/methodology for the full CLSG specification.",
            styles["Normal"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Test Cases", styles["Heading3"]),
    ]

    case_rows = [["ID", "Category", "Intent"]]
    for tc in test_cases:
        case_rows.append([tc.id, tc.intent_category, tc.intent])
    story.append(_table(case_rows))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Scores", styles["Heading3"]))
    score_rows = [["Model", "Language", "Safety", "Refusal Consistency", "Instruction Following"]]
    for r in results:
        score_rows.append(
            [r.model_id, r.form.value, f"{r.safety_score:.1f}", f"{r.refusal_consistency:.1f}", f"{r.instruction_following:.1f}"]
        )
    story.append(_table(score_rows))

    gap = average_clsg(results, reference_form)
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Cross-Lingual Safety Gap (CLSG)", styles["Heading3"]))
    story.append(
        Paragraph(
            f"Average CLSG relative to {reference_form.value}: {gap} points. "
            "CLSG is a VERIAUDIT proposed metric and has not been independently validated.",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Limitations", styles["Heading3"]))
    story.append(
        Paragraph(
            "Results depend on translation quality, embedding-based similarity screening, "
            "evaluator design, and sampling variance. Sample sizes in the pilot dataset are "
            "limited. See /docs/research.md for a full limitations discussion.",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(DISCLAIMER, small))

    doc.build(story)
    return buffer.getvalue()


def _table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f6b52")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f0ec")]),
            ]
        )
    )
    return table
