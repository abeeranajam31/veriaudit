# Safeguard verification (pre-data-collection, 2026-11-13)

This record checks that the eleven integrity fixes from the review round actually stop the failures
they were written for, rather than only passing their own unit tests.

## Method

Unit tests written for the new code mostly fail on the old code through API differences, such as a
missing keyword or a renamed function. That proves nothing about behaviour. Instead,
`research/integrity/replay_review_scenarios.py` replays each original failure as an end-to-end
scenario against any source tree. It uses only the public entry points: CLI functions, the
assembler, the runner and the analysis loader. It classifies each outcome as:

- **BLOCKED**: the unsafe action was refused with a reason.
- **BYPASSED**: the unsafe outcome happened.
- **CRASHED** or **OTHER_REFUSAL**: the run failed for an unrelated reason. These count as failures
  of the harness, not as protection.

```bash
git worktree add /tmp/old e4fc1fc        # last commit before the fixes
PYTHONPATH=/tmp/old/backend python research/integrity/replay_review_scenarios.py /tmp/old --out results/integrity/replay_old.json
PYTHONPATH=backend          python research/integrity/replay_review_scenarios.py .        --out results/integrity/replay_new.json
```

## Results

| # | Scenario: the unsafe outcome on old code | Old (e4fc1fc) | Now |
|---|---|---|---|
| s01 | Adjudicated variant (adjudicator + 1 independent) cannot validate as verified | BYPASSED | BLOCKED |
| s02 | English source edited after translation; old translation and ratings still used | BYPASSED | BLOCKED |
| s03 | A reviewer adjudicates the row they reviewed. Refused by the CLI **and** by the rating layer, so hand-written ratings files are covered too | BYPASSED | BLOCKED |
| s04 | Excel "CSV" save in Windows-1252 turns Urdu into `???`, which is imported | BYPASSED | BLOCKED |
| s05 | A resumed run mixes two datasets or configs in one run directory | BYPASSED | BLOCKED |
| s06 | Revising a variant drops its machine-translation disclosure | BYPASSED | BLOCKED |
| s07 | An unfinished run (no generations hash) is analysed | BYPASSED | BLOCKED |
| s08 | A `--limit` smoke run counts as a complete run | BYPASSED | BLOCKED |
| s09 | A family smaller than the fixed 4 models × 3 forms passes as confirmatory | BYPASSED | BLOCKED |
| s10 | A single self-declared "panel" label becomes a final label | BYPASSED | BLOCKED |
| s11 | A non-release (fixture or rc) dataset is analysed as confirmatory | BYPASSED | BLOCKED |
| s12 | Labels from unregistered "human" IDs, such as `gpt-4o`, are accepted | BYPASSED | BLOCKED |
| s13 | Generations for records not in the dataset are silently analysed | BYPASSED | BLOCKED |

Summary: 13/13 bypassed on the old code; 13/13 blocked now. The outputs are in
`results/integrity/replay_{old,new}.json`.

The four items singled out for checking:

- **Source-change invalidation.** Covered by s02 and by the lifecycle test. After release, an edit
  to the English benign source makes the next release refuse ("incomplete"), and its stale
  translations are dropped from the candidate build.
- **Adjudicator independence.** Covered by s03. Raters of a row are not offered it for
  adjudication, the import refuses it, and `apply_equivalence_ratings` refuses role conflicts in
  hand-written ratings. The assembler turns that into a clean exit.
- **CSV encoding.** Covered by s04 and by the LibreOffice-parametrised lifecycle test. An `.xlsx` or
  UTF-8 CSV save keeps Urdu byte for byte; a Windows-1252 CSV save is refused and nothing is written.
- **Resumed runs.** Covered by s05. A run directory is bound to its dataset hash and config hash.

## Lifecycle test with real Urdu

`backend/tests/test_authoring_lifecycle.py` drives the real CLI through every stage:

1. benign authoring;
2. independent benign review;
3. translation in `.xlsx`;
4. revision;
5. two independent reviews, one with a concern;
6. third-person adjudication;
7. release `2.0.0` (all six variants verified, the adjudicated one marked `human_adjudicated`);
8. a refused re-release (immutability);
9. a post-release source edit (2.0.1 refused, stale variants dropped).

Every sheet is filled with openpyxl and re-saved through LibreOffice headless, the closest available
stand-in for Excel. The test asserts that Urdu text survives byte for byte. Bugs found by this test
and fixed:

- re-export dropped the translator's self-check fields, so re-importing an unchanged sheet failed;
- the corruption detector missed two-letter words turned into `??` and wrongly flagged `kya???`.

## Clean-checkout run

`git clone` of commit 6376640 into a fresh directory → `pytest -q`: **247 passed**. Then:

- `ruff check` / `ruff format --check`: clean;
- `reconstruct.py`: 191/191 matched;
- `benign_candidates.py`: all checks pass.

LibreOffice is needed for the three spreadsheet tests; without it they are skipped, not passed.

## Remaining weaknesses (not fixed; documented)

1. **Integrity hashes are self-reported.** Run manifests and dataset hashes detect accidents and
   naive edits, but anyone who can edit the files can recompute them. They are not signatures. For
   publication, the PI should archive the run directories and hashes externally (for example a
   Zenodo deposit or a signed tag) at the time of collection.
2. **One person, two rater IDs.** The registry is pseudonymous, so the code cannot detect the same
   person registered twice. Independence rests on the PI's attestation when registering raters
   (`data/annotators.json`).
3. **Sheet protection has no password.** It prevents accidents, not deliberate edits. Edits to
   locked text are caught at import by per-row checksums; edits to locked metadata columns that
   carry no checksum (for example `category`) are ignored, because the import reads only editable
   columns.
4. **Single-letter corruption.** A one-letter Urdu word turned into a lone `?` is not flagged by the
   corruption regex, because a lone `?` is ordinary punctuation. The script-ratio checks and
   independent review are the backstop. A whole-row cp1252 save is still caught, because it destroys
   more than one word.
5. **Old code, new tests.** The unit tests are not run against the old tree, since API changes make
   them fail for irrelevant reasons. The behavioural replay is the evidence instead, and it covers
   the 11 fixes as 13 scenarios: s03 covers both the CLI and the rating layer, and s12–s13 cover the
   loader.
6. **Excel itself was not tested.** LibreOffice stands in for it. Excel's "CSV UTF-8" option should
   behave like the UTF-8 case, and plain "CSV" like the cp1252 case. The translator guide tells people
   to keep `.xlsx`. One real Excel round trip by the PI before translators start (G-list item) would
   close this gap.
