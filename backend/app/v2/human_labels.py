"""Human response labelling (protocol §8): the J0 judge check on the calibration pilot and the
main-study validation sample. Annotators work in .xlsx sheets like the translation workflow.

    PYTHONPATH=backend python -m app.v2.human_labels sample  --run RUN --labels JUDGE_LABELS... [--per-form 40]
    PYTHONPATH=backend python -m app.v2.human_labels export  --run RUN --annotator an01
    PYTHONPATH=backend python -m app.v2.human_labels import  FILLED.xlsx --run RUN --annotator an01
    PYTHONPATH=backend python -m app.v2.human_labels export-adjudication --run RUN --adjudicator adj01
    PYTHONPATH=backend python -m app.v2.human_labels import-adjudication FILLED.xlsx --run RUN --adjudicator adj01

Design:
- The sample is drawn ONCE, before any human label exists, and saved
  (results/v2/labels/human/<run>_sample.json). It is stratified by form x intent type and fills up to
  half of each stratum with responses on which the primary judges disagree (or one failed to
  parse); the rest is a hash-ordered random draw. Re-running `sample` refuses to overwrite.
- Sheets are blind: no model name, no judge label, no other annotator's label. Item order is
  shuffled by a fixed hash.
- Every row carries a checksum of the request and response it shows; an import refuses edited text,
  unregistered annotators, missing required labels and labels that do not fit the intent type.
- Two annotators label independently (label_source human). Rows where they disagree on any axis go
  to a third person (never one of the two annotators), whose decision is human_adjudicated.
- Re-importing a sheet replaces that annotator's file (one label per annotator per response).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from app.v2.records import Behaviour, Comprehension, Generation, LabelSource, ResponseLabel, TaskSuccess, append_jsonl
from app.veriaudit_x.authoring import (
    RESPONSE_ADJ_COLUMNS,
    RESPONSE_LABEL_COLUMNS,
    WorkflowError,
    _check_registered,
    check,
    load_registry,
    read_table,
    write_sheet,
)

ROOT = Path(__file__).resolve().parents[3]
LABEL_COLUMNS, ADJ_COLUMNS = RESPONSE_LABEL_COLUMNS, RESPONSE_ADJ_COLUMNS
SAMPLE_SEED = "veriaudit-j0"


def _h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _norm(text: str | None) -> str:
    """Spreadsheets drop leading/trailing whitespace and may turn \r\n into \n; the checksum ignores
    exactly that, so any other edit to a request or response is still caught."""
    return (text or "").replace("\r\n", "\n").strip()


def _sig(g: Generation) -> str:
    return check(g.generation_id, _norm(g.prompt_text), _norm(g.response_text))


def _key(lab: ResponseLabel) -> tuple:
    return (lab.comprehension, lab.behaviour, lab.harmful_content, lab.task_success)


def draw_sample(gens: list[Generation], judge_labels: list[ResponseLabel], per_form: int = 40, seed: str = SAMPLE_SEED) -> list[str]:
    """Generation ids: per form, per_form // 2 harmful + per_form // 2 benign; within each stratum up
    to half are judge disagreements (fewer than 2 distinct judges, or judges disagreeing)."""
    by_gen: dict[str, dict[str, ResponseLabel]] = defaultdict(dict)
    for lab in judge_labels:
        if lab.label_source == LabelSource.ai_judge:
            by_gen[lab.generation_id].setdefault(lab.labeler_id, lab)
    strata: dict[tuple, list[Generation]] = defaultdict(list)
    for g in gens:
        if g.error is None and g.response_text is not None:
            strata[(g.language, g.scenario_type)].append(g)
    chosen = []
    for (_, _), items in sorted(strata.items()):
        k = per_form // 2
        items = sorted(items, key=lambda g: _h(seed, g.generation_id))
        disagree = [g for g in items if len(by_gen[g.generation_id]) < 2 or len({_key(x) for x in by_gen[g.generation_id].values()}) > 1]
        take = disagree[: k // 2]
        rest = [g for g in items if g not in take]
        chosen += [g.generation_id for g in take + rest[: k - len(take)]]
    return chosen


def _row(item: int, g: Generation, rec: dict) -> dict:
    return {
        "item_id": f"L{item:04d}",
        "generation_id": g.generation_id,
        "intent_type": g.scenario_type,
        "language": g.language,
        "intent_description": rec["intent_description"],
        "request": g.prompt_text,
        "response": g.response_text,
        "source_check": _sig(g),
    }


def export_label_sheet(sample: list[str], gens: dict[str, Generation], records: dict[str, dict], annotator: str) -> list[dict]:
    order = sorted(sample, key=lambda gid: _h(SAMPLE_SEED, "order", gid))  # same order for every annotator; not by model or form
    return [_row(i, gens[gid], records[gens[gid].record_id]) | dict.fromkeys(LABEL_COLUMNS[8:], "") for i, gid in enumerate(order, 1)]


def _parse_label(row: dict, g: Generation, who: str, source: LabelSource, where: str, problems: list[str], note_col: str) -> ResponseLabel | None:
    if not any(row.get(c) for c in ("comprehension", "behaviour", "harmful_content", "task_success")):
        return None  # untouched row: skipped
    if row["source_check"] != _sig(g) or _norm(row["request"]) != _norm(g.prompt_text) or _norm(row["response"]) != _norm(g.response_text):
        problems.append(f"{where}: request/response or generation_id was edited (source_check mismatch)")
        return None
    harmful = g.scenario_type == "harmful"
    try:
        hc = {"yes": True, "no": False, "": None}[row["harmful_content"]]
        lab = ResponseLabel(
            generation_id=g.generation_id,
            labeler_id=who,
            label_source=source,
            comprehension=Comprehension(row["comprehension"]),
            behaviour=Behaviour(row["behaviour"]),
            harmful_content=hc,
            task_success=TaskSuccess(row["task_success"]) if row["task_success"] else None,
            rationale=(row.get(note_col) or "")[:500] or None,
        )
    except (KeyError, ValueError) as exc:
        problems.append(f"{where}: invalid or missing label value ({exc})")
        return None
    if harmful and (lab.harmful_content is None or lab.task_success is not None):
        problems.append(f"{where}: harmful request needs harmful_content (yes/no) and no task_success")
        return None
    if not harmful and (lab.task_success is None or lab.harmful_content is not None):
        problems.append(f"{where}: benign request needs task_success and no harmful_content")
        return None
    return lab


def import_label_sheet(path: Path, annotator: str, gens: dict[str, Generation], sample: list[str], registry: dict) -> list[ResponseLabel]:
    _check_registered(annotator, registry)
    problems, out = [], []
    allowed = set(sample)
    for n, row in enumerate(read_table(path, LABEL_COLUMNS), start=2):
        where = f"line {n} ({row.get('item_id')})"
        g = gens.get(row["generation_id"])
        if g is None or row["generation_id"] not in allowed:
            problems.append(f"{where}: generation_id not in the labelling sample")
            continue
        lab = _parse_label(row, g, annotator, LabelSource.human, where, problems, "notes")
        if lab:
            out.append(lab)
    if problems:
        raise WorkflowError(problems)
    return out


def disagreements(human: list[ResponseLabel]) -> dict[str, list[ResponseLabel]]:
    by: dict[str, dict[str, ResponseLabel]] = defaultdict(dict)
    for lab in human:
        if lab.label_source == LabelSource.human:
            by[lab.generation_id][lab.labeler_id] = lab
    return {g: list(v.values()) for g, v in by.items() if len(v) >= 2 and len({_key(x) for x in v.values()}) > 1}


def export_adjudication(dis: dict[str, list[ResponseLabel]], gens: dict[str, Generation], records: dict[str, dict], adjudicator: str) -> list[dict]:
    rows = []
    for i, gid in enumerate(sorted(dis, key=lambda x: _h(SAMPLE_SEED, "adj", x)), 1):
        if adjudicator in {lab.labeler_id for lab in dis[gid]}:
            continue  # never adjudicate a row you labelled
        summary = " || ".join(
            f"{lab.labeler_id}: {lab.comprehension.value}, {lab.behaviour.value}, "
            f"harmful={lab.harmful_content}, task={lab.task_success and lab.task_success.value}" + (f" ({lab.rationale})" if lab.rationale else "")
            for lab in dis[gid]
        )
        g = gens[gid]
        rows.append(_row(i, g, records[g.record_id]) | {"labels_summary": summary} | dict.fromkeys(ADJ_COLUMNS[9:], ""))
    return rows


def import_adjudication(path: Path, adjudicator: str, gens: dict[str, Generation], dis: dict[str, list[ResponseLabel]], registry: dict) -> list[ResponseLabel]:
    _check_registered(adjudicator, registry)
    problems, out = [], []
    for n, row in enumerate(read_table(path, ADJ_COLUMNS), start=2):
        where = f"line {n} ({row.get('item_id')})"
        gid = row["generation_id"]
        if gid not in dis:
            problems.append(f"{where}: not a disagreement between two annotators")
            continue
        if adjudicator in {lab.labeler_id for lab in dis[gid]}:
            problems.append(f"{where}: {adjudicator} labelled this response; the adjudicator must be a third person")
            continue
        lab = _parse_label(row, gens[gid], adjudicator, LabelSource.human_adjudicated, where, problems, "rationale")
        if lab and not lab.rationale:
            problems.append(f"{where}: rationale is required")
        elif lab:
            out.append(lab)
    if problems:
        raise WorkflowError(problems)
    return out


# --------------------------------------------------------------------------- CLI


def _load(run: Path):
    from app.v2.inference.runner import load_generations

    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    ds = Path(manifest["dataset"]["path"])
    ds = ds if ds.is_absolute() else ROOT / ds
    if hashlib.sha256(ds.read_bytes()).hexdigest() != manifest["dataset"]["sha256"]:
        raise SystemExit(f"dataset {ds} changed since the run")
    records = {r["record_id"]: r for r in map(json.loads, ds.read_text(encoding="utf-8").splitlines())}
    gens = {g.generation_id: g for g in load_generations(run / "generations.jsonl")}
    return manifest["run_id"], gens, records


def _read_labels(paths) -> list[ResponseLabel]:
    return [ResponseLabel.model_validate_json(x) for p in paths for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sample")
    p.add_argument("--labels", type=Path, nargs="*", default=[], help="AI-judge label files (to oversample disagreements)")
    p.add_argument("--per-form", type=int, default=40)
    for name in ("export", "import", "export-adjudication", "import-adjudication"):
        q = sub.add_parser(name)
        if name.startswith("import"):
            q.add_argument("path", type=Path)
        q.add_argument("--adjudicator" if "adjudication" in name else "--annotator", required=True, dest="person")
    for q in sub.choices.values():
        q.add_argument("--run", type=Path, required=True)
        q.add_argument("--out-dir", type=Path, default=ROOT / "results" / "v2" / "labels" / "human")
        q.add_argument("--registry", type=Path, default=ROOT / "data" / "annotators.json")
    args = ap.parse_args(argv)

    run_id, gens, records = _load(args.run)
    out = args.out_dir
    sample_file = out / f"{run_id}_sample.json"
    try:
        if args.cmd == "sample":
            if sample_file.exists():
                raise SystemExit(f"{sample_file} exists; the sample is drawn once (delete it only if no one has started labelling)")
            ids = draw_sample(list(gens.values()), _read_labels(args.labels), args.per_form)
            out.mkdir(parents=True, exist_ok=True)
            sample_file.write_text(json.dumps({"run_id": run_id, "per_form": args.per_form, "generation_ids": ids}, indent=1) + "\n", encoding="utf-8")
            print(f"{len(ids)} responses -> {sample_file}")
            return 0
        sample = json.loads(sample_file.read_text(encoding="utf-8"))["generation_ids"]
        registry = load_registry(args.registry)
        human_files = sorted(out.glob(f"{run_id}__human_*.jsonl"))
        if args.cmd == "export":
            _check_registered(args.person, registry)
            path = write_sheet(out / "sheets" / f"{run_id}_labels_{args.person}.xlsx", LABEL_COLUMNS, export_label_sheet(sample, gens, records, args.person))
            print(path)
        elif args.cmd == "import":
            labs = import_label_sheet(args.path, args.person, gens, sample, registry)
            dest = out / f"{run_id}__human_{args.person}.jsonl"
            dest.unlink(missing_ok=True)
            append_jsonl(dest, labs)
            print(f"{len(labs)} labels -> {dest} (replaces any earlier import by {args.person})")
        else:
            dis = disagreements(_read_labels(human_files))
            if args.cmd == "export-adjudication":
                _check_registered(args.person, registry)
                rows = export_adjudication(dis, gens, records, args.person)
                path = write_sheet(out / "sheets" / f"{run_id}_adjudication_{args.person}.xlsx", ADJ_COLUMNS, rows)
                print(f"{len(rows)} disagreements -> {path}")
            else:
                labs = import_adjudication(args.path, args.person, gens, dis, registry)
                dest = out / f"{run_id}__adjudicated_{args.person}.jsonl"
                dest.unlink(missing_ok=True)
                append_jsonl(dest, labs)
                print(f"{len(labs)} adjudicated labels -> {dest}")
    except WorkflowError as exc:
        print(f"IMPORT REFUSED - nothing was written.\n{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
