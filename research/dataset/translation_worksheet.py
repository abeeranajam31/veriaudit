"""Human authoring workflow for VeriAudit-X - command line (guide: docs/v2/translation_guide.md).

All files live in data/candidates/authoring/ (sheets/ = CSVs for people; *.jsonl = imports).
Every person ID must be registered as human in data/annotators.json.

Stage A - benign contrasts
  export-benign                          -> sheets/benign_authoring.csv
  import-benign FILE --author ID         -> benign_authored.jsonl
  export-benign-review --reviewer ID     -> sheets/benign_review_<ID>.csv   (never your own contrasts)
  import-benign-review FILE --reviewer ID-> benign_validity.jsonl
Stage B - translation
  export [--phase 1|2|all]               -> data/candidates/translation_worksheet.csv
  import FILE --translator ID            -> variants_<time>_<ID>.jsonl
Stage C - independent review and adjudication
  export-review --reviewer ID [--qc-sample 0.2] -> sheets/review_<ID>.csv  (never your own variants;
                                            --qc-sample: only the fixed third-person QC sample)
  import-review FILE --reviewer ID       -> ratings_<time>_<ID>.jsonl
  export-adjudication --adjudicator ID   -> sheets/adjudication_<ID>.csv
  import-adjudication FILE --adjudicator ID -> ratings_<time>_<ID>.jsonl
status                                   -> authoring/STATUS.md

Run from the repo root with PYTHONPATH=backend. Every export writes a UTF-8 .csv and an .xlsx
(use the .xlsx in Excel: plain-CSV saves destroy Urdu). Imports accept either. An import with any
problem writes nothing and lists every problem; fix the sheet and import again.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.veriaudit_x import authoring as A

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
AUTH = CAND / "authoring"
SHEETS = AUTH / "sheets"
REGISTRY = ROOT / "data" / "annotators.json"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def selection() -> list[dict]:
    return load_jsonl(CAND / "selection.jsonl")


def subset() -> set[str]:
    return set(json.loads((CAND / "transformation_subset.json").read_text(encoding="utf-8")))


def authored_benign() -> dict[str, dict]:
    return {r["scenario_id"]: r for r in load_jsonl(AUTH / "benign_authored.jsonl")}  # later lines win


def plan() -> tuple[list[A.PlannedRow], list[str]]:
    return A.plan_rows(selection(), subset(), authored_benign())


def variants(rows: list[A.PlannedRow]) -> dict[str, dict]:
    return A.current_variants(rows, A.load_variants(sorted(AUTH.glob("variants_*.jsonl"))))


def ratings() -> list[dict]:
    out = []
    for p in sorted(AUTH.glob("ratings_*.jsonl")):
        out += load_jsonl(p)
    return out


def registered(person: str) -> None:
    A._check_registered(person, A.load_registry(REGISTRY))


def emit(path: Path, columns: list[str], rows: list[dict]) -> str:
    """Write the sheet as UTF-8 CSV (canonical, diffable) and as .xlsx (for people: locked read-only
    columns, dropdowns, right-to-left Urdu) next to each other."""
    csv_path = A.write_csv(Path(path).with_suffix(".csv"), columns, rows)
    xlsx_path = A.write_xlsx(SHEETS / (Path(path).stem + ".xlsx"), columns, rows)
    return f"{csv_path}\n{xlsx_path}"


def status() -> Path:
    rows, waiting = plan()
    v = variants(rows)
    rs = ratings()
    validity = load_jsonl(AUTH / "benign_validity.jsonl")
    ab = authored_benign()
    need_benign = [c["scenario_id"] for c in selection() if not c.get("benign_en")]
    reviewed_ok = {r["scenario_id"] for r in validity if r["benign"] and r["topically_matched"]}
    by_row: dict[str, set] = defaultdict(set)
    for r in rs:
        vv = v.get(r["record_id"])
        if vv and r.get("text_sha256") == vv["text_sha256"] and r["rater_role"] == "independent_reviewer":
            by_row[r["record_id"]].add(r["annotator_id"])  # unique raters, not rating rows
    lines = [
        "# Authoring status",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. Counts only; nothing here is a result.",
        "",
        "| Stage | Done | Total |",
        "|---|---|---|",
        f"| A. benign contrasts written | {sum(s in ab for s in need_benign)} | {len(need_benign)} |",
        f"| A. benign contrasts passing review | {sum(s in reviewed_ok for s in need_benign)} | {len(need_benign)} |",
    ]
    for phase in (1, 2):
        pr = [r for r in rows if r.phase == phase]
        lines.append(f"| B. phase {phase} variants written | {sum(r.row_id in v for r in pr)} | {len(pr)} (planned so far) |")
        lines.append(f"| C. phase {phase} variants with >= 2 current independent ratings | {sum(len(by_row[r.row_id]) >= 2 for r in pr)} | {len(pr)} |")
    lines += ["", f"Scenarios whose benign rows cannot be planned until stage A is done: {len(waiting)}"]
    out = AUTH / "STATUS.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export-benign")
    for name, who in (
        ("import-benign", "--author"),
        ("import-benign-review", "--reviewer"),
        ("import", "--translator"),
        ("import-review", "--reviewer"),
        ("import-adjudication", "--adjudicator"),
    ):
        p = sub.add_parser(name)
        p.add_argument("path", type=Path)
        p.add_argument(who, required=True, dest="person")
    for name, who in (("export-benign-review", "--reviewer"), ("export-review", "--reviewer"), ("export-adjudication", "--adjudicator")):
        p = sub.add_parser(name)
        p.add_argument(who, required=True, dest="person")
        if name == "export-review":
            p.add_argument("--qc-sample", type=float, metavar="FRACTION", help="only the fixed QC sample of scenarios (e.g. 0.2)")
    sub.add_parser("export").add_argument("--phase", choices=["1", "2", "all"], default="all")
    sub.add_parser("status")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "export-benign":
            out = emit(SHEETS / "benign_authoring.csv", A.BENIGN_COLUMNS, A.export_benign_authoring(selection(), authored_benign()))
        elif args.cmd == "import-benign":
            registered(args.person)
            rows = A.import_benign_authoring(args.path, args.person, selection())
            append_jsonl(AUTH / "benign_authored.jsonl", rows)
            out = f"{len(rows)} benign contrasts imported (each now needs a review by someone else)"
        elif args.cmd == "export-benign-review":
            registered(args.person)
            out = emit(
                SHEETS / f"benign_review_{args.person}.csv", A.BENIGN_REVIEW_COLUMNS, A.export_benign_review(selection(), authored_benign(), args.person)
            )
        elif args.cmd == "import-benign-review":
            registered(args.person)
            rows = A.import_benign_review(args.path, args.person, selection(), authored_benign())
            append_jsonl(AUTH / "benign_validity.jsonl", rows)
            out = f"{len(rows)} benign-validity reviews imported"
        elif args.cmd == "export":
            rows, waiting = plan()
            phases = (1, 2) if args.phase == "all" else (int(args.phase),)
            sheet = A.export_worksheet(rows, phases)
            done = variants(rows)
            for r in sheet:  # show already-imported work so translators do not redo it
                if r["locked"] == "no" and r["row_id"] in done:
                    d = done[r["row_id"]]
                    sa = d.get("self_assessment") or {}
                    hp = sa.get("harm_preserved")
                    r.update(
                        text=d["text"],
                        status="done",
                        drafting_aid=d.get("drafting_aid") or "",
                        self_equivalence=sa.get("equivalence") or "",
                        self_harm_preserved={True: "yes", False: "no"}.get(hp, "unsure" if sa else ""),
                        naturalness=str(sa.get("naturalness") or ""),
                        ambiguity=sa.get("ambiguity") or "",
                        comments=sa.get("comments") or f"imported from {d['author_id']}",
                    )
            out = emit(CAND / "translation_worksheet.csv", A.WORKSHEET_COLUMNS, sheet)
            if waiting:
                print(f"note: benign rows for {len(waiting)} scenarios appear after their benign contrast is written (stage A)", file=sys.stderr)
        elif args.cmd == "import":
            registered(args.person)
            rows, _ = plan()
            prev = variants(rows)
            res = A.import_worksheet(args.path, args.person, rows, previous=prev)
            new = [x for x in res.variants if not (x["status"] == "done" and prev.get(x["row_id"], {}).get("text") == x["text"])]
            for x in new:
                x["imported_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if new:
                append_jsonl(AUTH / f"variants_{stamp()}_{args.person}.jsonl", new)
            for w in res.warnings:
                print("warning:", w, file=sys.stderr)
            n_done = sum(x["status"] == "done" for x in new)
            n_cannot = sum(x["status"] == "cannot_translate" for x in new)
            out = f"{n_done} new or revised variants, {n_cannot} marked cannot_translate"
        elif args.cmd == "export-review":
            registered(args.person)
            rows, _ = plan()
            v = variants(rows)
            rated = {(r["record_id"], r.get("text_sha256")) for r in ratings() if r["annotator_id"] == args.person}
            items = A.export_review(rows, v, args.person, rated)
            if args.qc_sample:
                sample = A.qc_sample({c["scenario_id"] for c in selection()}, args.qc_sample)
                items = [r for r in items if A.scenario_of(r["row_id"]) in sample]
            out = emit(SHEETS / f"review_{args.person}.csv", A.REVIEW_COLUMNS, items)
        elif args.cmd == "import-review":
            rows, _ = plan()
            rs = A.import_review(args.path, args.person, rows, variants(rows), A.load_registry(REGISTRY))
            append_jsonl(AUTH / f"ratings_{stamp()}_{args.person}.jsonl", rs)
            out = f"{len(rs)} ratings imported"
        elif args.cmd == "export-adjudication":
            registered(args.person)
            rows, _ = plan()
            out = emit(SHEETS / f"adjudication_{args.person}.csv", A.ADJUDICATION_COLUMNS, A.export_adjudication(rows, variants(rows), ratings(), args.person))
        elif args.cmd == "import-adjudication":
            rows, _ = plan()
            rs = A.import_adjudication(args.path, args.person, rows, variants(rows), A.load_registry(REGISTRY), ratings())
            append_jsonl(AUTH / f"ratings_{stamp()}_{args.person}.jsonl", rs)
            out = f"{len(rs)} adjudications imported"
        else:
            out = status()
    except A.WorkflowError as exc:
        print("IMPORT/EXPORT REFUSED - nothing was written.", file=sys.stderr)
        for p in exc.problems:
            print("  -", p, file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
