# data/

| Path | Contents |
|---|---|
| `sources/` | Licensed third-party seeds (AdvBench MIT, XSTest CC-BY-4.0), SHA-256 pinned in `SOURCES.json`; see `NOTICE.md` |
| `candidates/selection.jsonl` | 200 selected main-study scenarios (`research/dataset/build_candidates.py`), report in `selection_report.md` |
| `candidates/transformation_subset.json` | the 70 scenarios that get controlled transformations T1–T6 |
| `candidates/batches/` | variant-authoring batches |
| `candidates/translation_worksheet.csv` | human translation worksheet (400 rows = 200 scenarios × harmful/benign) |
| `candidates/generated/` | authored variants (AI or human), one JSONL per batch/translator — **empty**: AI generation was stopped by model safety classifiers; awaiting human translation |
| `veriaudit-x/<version>/` | assembled, validated release + QC report + scenario-grouped splits (`research/dataset/assemble_veriaudit_x.py`) — not yet built |
