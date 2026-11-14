"""Exploratory v0.1 replication: dataset, run config, T4 manifests and analysis wired end to end
(fake backend and synthetic labels only; nothing here is a result)."""

import importlib.util
import json
from pathlib import Path

import yaml

from app.v2.inference.runner import load_generations, run
from app.v2.records import LabelSource, ResponseLabel, append_jsonl

REPO = Path(__file__).resolve().parents[2]


def test_t4_manifests_keep_the_pinned_revisions():
    main = {m["key"]: m for m in yaml.safe_load((REPO / "configs/models.yaml").read_text())["models"]}
    t4 = {m["key"]: m for m in yaml.safe_load((REPO / "configs/models_kaggle_t4.yaml").read_text())["models"]}
    conf = {k for k, m in main.items() if m.get("confirmatory")}
    assert conf <= set(t4)
    for k in conf:
        assert t4[k]["revision"] == main[k]["revision"] and t4[k]["model_id"] == main[k]["model_id"]


def test_exploratory_pipeline_on_fake_backend(tmp_path):
    ds = json.loads((REPO / "data/veriaudit-x/exploratory-v01/manifest.json").read_text())
    assert ds["n_records"] == 120 and ds["is_exploratory"] and not ds["is_release"]
    gfile = run(REPO / "configs/experiments/exploratory_v01_panel.yaml", ["fake"], out_root=tmp_path)
    gens = load_generations(gfile)
    lab = tmp_path / "labels.jsonl"
    rows = []
    for g in gens:
        harmful = g.language == "urdu" and g.scenario_id < "VX-S0016"  # synthetic: Urdu more often "harmful"
        for j in ("ja@r", "jb@r"):
            rows.append(ResponseLabel(generation_id=g.generation_id, labeler_id=j, label_source=LabelSource.ai_judge, comprehension="understood",
                                      behaviour="full_compliance" if harmful else "full_refusal", harmful_content=harmful, is_test_fixture=True))  # fmt: skip
    append_jsonl(lab, rows)
    spec = importlib.util.spec_from_file_location("expl", REPO / "research/analysis/exploratory_v01_panel.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.analyse(gfile.parent, [lab], tmp_path / "out", REPO / "configs/models.yaml", n_boot=100, allow_fixtures=True)
    urdu = next(r for r in res["h1"] if r["language"] == "urdu")
    assert urdu["n_pairs"] == 30 and abs(urdu["gap_pp"] - 50.0) < 1e-9
    assert "EXPLORATORY" in (tmp_path / "out/summary.md").read_text()


def test_runner_batches_and_retries_failed_batches(tmp_path):
    from app.v2.inference.backends import BackendError, FakeBackend, GenResult

    class Batched(FakeBackend):
        batches: int = 0
        fail_first: bool = True

        def generate_batch_full(self, batch, decoding):
            self.batches += 1
            if self.fail_first:
                self.fail_first = False
                raise BackendError("simulated OOM")
            return [self.generate_full(m, decoding) for m in batch]

    b = Batched()
    gfile = run(REPO / "configs/experiments/exploratory_v01_panel.yaml", ["fake"], backend_override=b, out_root=tmp_path)
    gens = load_generations(gfile)
    assert len(gens) == 120 * 4 and all(g.error is None for g in gens)
    assert b.batches == 5  # 4 decodings, one batch each, plus one retry of the failed batch
    assert json.loads((gfile.parent / "run_manifest.json").read_text())["status"] == "complete"
    assert isinstance(GenResult("x"), GenResult)
