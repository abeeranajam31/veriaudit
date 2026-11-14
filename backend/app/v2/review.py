"""Human review support: prioritised queues and merging human equivalence ratings.

Priority order for variant review (highest first):
  0 flagged by automated screen or reviewer   1 failed automated check   2 controlled transformation
  3 AI-generated base variant                 4 other pending
Priority for response-label review: unresolved AI disagreement first, then low-confidence
AI labels, then a random stratified spot-check sample.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from app.v2.records import LabelSource, ResponseLabel
from app.veriaudit_x.schema import EquivalenceJudgement, EquivalenceRating, EquivalenceStatus, RaterRole, VeriAuditXRecord


def variant_priority(r: VeriAuditXRecord) -> int:
    if r.equivalence.status == EquivalenceStatus.flagged:
        return 0
    if any(not c.passed for c in r.quality.automated_checks.values()):
        return 1
    if r.transformation.parameters.get("condition", "base") != "base":
        return 2
    if r.quality.ai_generated:
        return 3
    return 4


def variant_queue(records: Iterable[VeriAuditXRecord]) -> list[VeriAuditXRecord]:
    todo = [r for r in records if r.equivalence.status in (EquivalenceStatus.pending, EquivalenceStatus.flagged)]
    return sorted(todo, key=lambda r: (variant_priority(r), r.record_id))


def apply_equivalence_ratings(record: VeriAuditXRecord, ratings: list[EquivalenceRating], min_raters: int = 2) -> VeriAuditXRecord:
    """Add HUMAN ratings and recompute status (translation_guide.md §6).

    - A rating by the variant's author is refused; a rating of a different text version is refused.
    - A rater's latest rating replaces their earlier one.
    - Without an adjudicator: verified needs >= `min_raters` independent ratings, all 'equivalent'
      with harm preserved; any 'not_equivalent' or harm_preserved=false -> rejected (once
      `min_raters` have rated) else flagged; any 'partially_equivalent' -> flagged.
    - With an adjudicator: their decision settles it (equivalent -> verified only if at least one
      independent reviewer also rated 'equivalent'; partially -> flagged for revision; not -> rejected),
      and quality.human_adjudicated is set.
    Similarity scores and AI reviews are never inputs here.
    """
    if record.equivalence.status == EquivalenceStatus.source:
        raise ValueError("source records are not rated")
    author = record.transformation.author_id
    text_hash = hashlib.sha256(record.text.encode("utf-8")).hexdigest()
    for r in ratings:
        if author and r.annotator_id == author:
            raise ValueError(f"{author} authored {record.record_id}; an author's rating cannot count as review")
        if r.text_sha256 is not None and r.text_sha256 != text_hash:
            raise ValueError(f"rating by {r.annotator_id} for {record.record_id} refers to a different text version")
    existing = {h.annotator_id: h for h in record.equivalence.human_ratings}
    for r in ratings:
        prev = existing.get(r.annotator_id)
        if prev is not None and prev.rater_role != r.rater_role:
            # e.g. a reviewer adjudicating their own row: would silently replace their own rating
            raise ValueError(f"{r.annotator_id} already rated {record.record_id} as {prev.rater_role.value}; cannot also act as {r.rater_role.value}")
    roles_in_batch: dict[str, set] = {}
    for r in ratings:
        roles_in_batch.setdefault(r.annotator_id, set()).add(r.rater_role)
    if any(len(v) > 1 for v in roles_in_batch.values()):
        raise ValueError(f"{record.record_id}: the same person appears as reviewer and adjudicator")
    by_rater = dict(existing)
    for r in ratings:
        by_rater[r.annotator_id] = r
    all_r = sorted(by_rater.values(), key=lambda h: h.annotator_id)
    independent = [h for h in all_r if h.rater_role == RaterRole.independent_reviewer]
    adjudicators = [h for h in all_r if h.rater_role == RaterRole.adjudicator]
    if len(adjudicators) > 1:
        raise ValueError(f"{record.record_id}: more than one adjudicator")

    def accepts(h: EquivalenceRating) -> bool:
        return h.judgement == EquivalenceJudgement.equivalent and h.harm_preserved is not False

    adjudicated = bool(adjudicators)
    if adjudicated:
        adj = adjudicators[0]
        if adj.judgement == EquivalenceJudgement.not_equivalent or adj.harm_preserved is False:
            status = EquivalenceStatus.rejected
        elif accepts(adj) and any(accepts(h) for h in independent):
            status = EquivalenceStatus.verified
        else:
            status = EquivalenceStatus.flagged
    elif any(h.judgement == EquivalenceJudgement.not_equivalent or h.harm_preserved is False for h in independent):
        status = EquivalenceStatus.rejected if len(independent) >= min_raters else EquivalenceStatus.flagged
    elif len(independent) >= min_raters and all(accepts(h) for h in independent):
        status = EquivalenceStatus.verified
    elif any(h.judgement == EquivalenceJudgement.partially_equivalent for h in independent):
        status = EquivalenceStatus.flagged
    else:
        status = EquivalenceStatus.pending
    eq = record.equivalence.model_copy(update={"human_ratings": all_r, "status": status})
    q = record.quality.model_copy(update={"human_reviewed": True, "human_adjudicated": record.quality.human_adjudicated or adjudicated})
    return record.model_copy(update={"equivalence": eq, "quality": q})


def label_queue(labels: Iterable[ResponseLabel], spot_check_rate: float = 0.05, seed: int = 0) -> list[tuple[str, str]]:
    """(generation_id, reason) in review order."""
    by_gen: dict[str, list[ResponseLabel]] = {}
    for lab in labels:
        by_gen.setdefault(lab.generation_id, []).append(lab)
    out = []
    for gid, labs in by_gen.items():
        if any(lab.label_source in (LabelSource.human, LabelSource.human_adjudicated) for lab in labs):
            continue
        keys = {(lab.comprehension, lab.behaviour, lab.harmful_content, lab.task_success) for lab in labs}
        if len(keys) > 1:
            out.append((0, gid, "ai_disagreement"))
        elif any(lab.confidence is not None and lab.confidence < 0.7 for lab in labs):
            out.append((1, gid, "low_confidence"))
        elif int(hashlib.sha256(f"{seed}:{gid}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < spot_check_rate:
            out.append((2, gid, "random_spot_check"))
    return [(gid, reason) for _, gid, reason in sorted(out)]
