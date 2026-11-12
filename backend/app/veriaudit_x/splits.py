"""Leakage-free train / validation / test splits for VeriAudit-X.

Unit of assignment
------------------
Splits are assigned to *scenario groups*, never to individual records or
intents. A scenario group is a connected component of scenarios joined by
any of these links:

* the same scenario_id (all of a scenario's intents and variants),
* identical normalised text appearing in two scenarios,
* a transformation/equivalence reference or contrast pair that crosses
  scenarios (the validator reports these as errors, but splitting still
  unions them so a dirty file cannot leak).

Every linguistic variant of an intent therefore lands in the same split as
its source text, and a harmful intent always lands with its benign contrast.

Allocation
----------
Groups are ordered by stratum (the set of scenario_type/category pairs they
contain), then by a seeded hash inside each stratum, and assigned greedily
to whichever split is furthest below its target share (counted in
scenarios). This is systematic allocation along a stratum-sorted list: it
hits the global ratios to within one group and spreads each stratum across
splits, but per-stratum proportions are only approximate when strata are
small. The allocation is fully determined by (records, seed, ratios).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.veriaudit_x.normalize import normalize_text
from app.veriaudit_x.schema import VeriAuditXRecord
from app.veriaudit_x.validation import VALID_SPLITS, ValidationIssue

DEFAULT_RATIOS = (0.70, 0.15, 0.15)


class SplitLeakageError(RuntimeError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("\n".join(i.format() for i in issues))


@dataclass
class SplitResult:
    assignment: dict[str, str]  # scenario_id -> split
    groups: list[list[str]]  # scenario groups, each sorted
    seed: int
    ratios: tuple[float, float, float]

    def split_of(self, record: VeriAuditXRecord) -> str:
        return self.assignment[record.scenario_id]

    def apply(self, records: list[VeriAuditXRecord]) -> dict[str, list[VeriAuditXRecord]]:
        out: dict[str, list[VeriAuditXRecord]] = {s: [] for s in VALID_SPLITS}
        for r in records:
            out[self.split_of(r)].append(r.model_copy(update={"split": self.split_of(r)}))
        return out


class _UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # deterministic root choice
            lo, hi = sorted((ra, rb))
            self.parent[hi] = lo


def _validate_ratios(ratios) -> tuple[float, float, float]:
    ratios = tuple(float(x) for x in ratios)
    if len(ratios) != 3 or any(x < 0 for x in ratios) or abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError(f"ratios must be three non-negative numbers summing to 1, got {ratios}")
    return ratios  # type: ignore[return-value]


def scenario_groups(records: list[VeriAuditXRecord]) -> list[list[str]]:
    scenarios = sorted({r.scenario_id for r in records})
    uf = _UnionFind(scenarios)
    by_record = {r.record_id: r for r in records}
    intent_scenario = {r.intent_id: r.scenario_id for r in records}

    text_owner: dict[str, str] = {}
    for r in records:
        key = normalize_text(r.text)
        if key in text_owner:
            uf.union(text_owner[key], r.scenario_id)
        else:
            text_owner[key] = r.scenario_id
        for ref in (r.transformation.source_record_id, r.equivalence.reference_record_id):
            if ref in by_record:
                uf.union(r.scenario_id, by_record[ref].scenario_id)
        if r.contrast_intent_id in intent_scenario:
            uf.union(r.scenario_id, intent_scenario[r.contrast_intent_id])

    groups: dict[str, list[str]] = defaultdict(list)
    for s in scenarios:
        groups[uf.find(s)].append(s)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def _seeded_key(seed: int, text: str) -> str:
    return hashlib.sha256(f"{seed}:{text}".encode()).hexdigest()


def assign_splits(
    records: list[VeriAuditXRecord],
    seed: int = 13,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
) -> SplitResult:
    if not records:
        raise ValueError("cannot split an empty dataset")
    ratios = _validate_ratios(ratios)
    groups = scenario_groups(records)

    strata_of_scenario: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for r in records:
        strata_of_scenario[r.scenario_id].add((r.scenario_type.value, r.category.value))

    def stratum(group: list[str]) -> tuple:
        return tuple(sorted(set().union(*(strata_of_scenario[s] for s in group))))

    ordered = sorted(groups, key=lambda g: (stratum(g), _seeded_key(seed, g[0])))

    counts = dict.fromkeys(VALID_SPLITS, 0)
    assignment: dict[str, str] = {}
    total = 0
    for group in ordered:
        weight = len(group)
        total += weight
        deficits = {s: ratio * total - counts[s] for s, ratio in zip(VALID_SPLITS, ratios)}
        # ties resolved by VALID_SPLITS order; zero-ratio splits never chosen
        choice = max((s for s, ratio in zip(VALID_SPLITS, ratios) if ratio > 0), key=lambda s: deficits[s])
        counts[choice] += weight
        for scenario_id in group:
            assignment[scenario_id] = choice

    result = SplitResult(assignment=assignment, groups=groups, seed=seed, ratios=ratios)
    issues = check_leakage(result.apply(records))
    if issues:  # cannot happen if grouping is correct; guard against regressions
        raise SplitLeakageError(issues)
    return result


def check_leakage(splits: dict[str, list[VeriAuditXRecord]]) -> list[ValidationIssue]:
    """Report anything that would let information cross split boundaries."""
    issues: list[ValidationIssue] = []
    where: dict[str, dict[str, set[str]]] = {
        "scenario_id": defaultdict(set),
        "intent_id": defaultdict(set),
        "text": defaultdict(set),
    }
    split_of_record: dict[str, str] = {}
    split_of_intent: dict[str, set[str]] = defaultdict(set)
    for split, recs in splits.items():
        for r in recs:
            where["scenario_id"][r.scenario_id].add(split)
            where["intent_id"][r.intent_id].add(split)
            where["text"][normalize_text(r.text)].add(split)
            split_of_record[r.record_id] = split
            split_of_intent[r.intent_id].add(split)

    for kind, table in where.items():
        for key, found in sorted(table.items()):
            if len(found) > 1:
                issues.append(
                    ValidationIssue("error", "split_leakage", f"{kind} {key!r} appears in {sorted(found)}", field=kind)
                )

    for split, recs in splits.items():
        for r in recs:
            for ref in (r.transformation.source_record_id, r.equivalence.reference_record_id):
                if ref in split_of_record and split_of_record[ref] != split:
                    issues.append(
                        ValidationIssue("error", "split_leakage", f"derived from {ref} in {split_of_record[ref]}", record_id=r.record_id)
                    )
            c = r.contrast_intent_id
            if c in split_of_intent and split_of_intent[c] != {split}:
                issues.append(
                    ValidationIssue("error", "split_leakage", f"contrast intent {c} is in {sorted(split_of_intent[c])}", record_id=r.record_id)
                )
    return issues


def split_statistics(splits: dict[str, list[VeriAuditXRecord]]) -> dict:
    stats = {}
    for split, recs in splits.items():
        stats[split] = {
            "records": len(recs),
            "scenarios": len({r.scenario_id for r in recs}),
            "intents": len({r.intent_id for r in recs}),
            "by_scenario_type": dict(sorted(Counter(r.scenario_type.value for r in recs).items())),
            "by_category": dict(sorted(Counter(r.category.value for r in recs).items())),
            "by_language": dict(sorted(Counter(r.language.value for r in recs).items())),
        }
    return stats


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_splits(
    records: list[VeriAuditXRecord],
    out_dir: Path,
    seed: int = 13,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    source_file: Path | None = None,
    dataset_version: str | None = None,
) -> dict:
    """Write train/validation/test JSONL files and a split_manifest.json; return the manifest."""
    result = assign_splits(records, seed=seed, ratios=ratios)
    splits = result.apply(records)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for split, recs in splits.items():
        with (out_dir / f"{split}.jsonl").open("w", encoding="utf-8") as f:
            for r in sorted(recs, key=lambda x: x.record_id):
                f.write(json.dumps(r.model_dump(mode="json"), ensure_ascii=False) + "\n")

    manifest = {
        "dataset_version": dataset_version,
        "schema_version": records[0].schema_version,
        "source_file": str(source_file) if source_file else None,
        "source_sha256": _sha256(source_file) if source_file else None,
        "seed": seed,
        "ratios": dict(zip(VALID_SPLITS, result.ratios)),
        "split_unit": "scenario group (scenario_id, unioned over shared normalised text and cross-scenario references)",
        "statistics": split_statistics(splits),
        "scenario_groups": [g for g in result.groups if len(g) > 1],
        "assignment": dict(sorted(result.assignment.items())),
    }
    (out_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
