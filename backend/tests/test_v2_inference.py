"""CPU tests of the inference pipeline with the FakeBackend (outputs are test fixtures, never results)."""

import json
from pathlib import Path

import pytest
import yaml

from app.v2.inference.backends import BackendError, FakeBackend, OpenAICompatibleBackend, build_backend
from app.v2.inference.runner import ROOT, RunConfigError, check_pinned, generation_id, load_generations, load_yaml, plan, run, select_models
from app.v2.judges.llm_judge import LLMJudge
from app.v2.metrics import build_units, cell_metrics
from app.v2.records import Decoding, Generation, read_jsonl, resolve_labels

SMOKE = ROOT / "configs" / "experiments" / "fixture_smoke.yaml"


def test_plan_has_greedy_plus_three_samples():
    p = plan(load_yaml(SMOKE))
    assert [i for i, _ in p] == [-1, 0, 1, 2]
    assert p[0][1].temperature == 0.0 and p[1][1].seed == 0


def test_model_manifest_is_well_formed():
    models = load_yaml(ROOT / "configs" / "models.yaml")["models"]
    keys = [m["key"] for m in models]
    assert len(keys) == len(set(keys))
    assert {"qwen3_8b", "aya_expanse_8b"} <= set(keys)
    for m in models:
        assert m["backend"] in {"transformers", "vllm", "openai_compatible", "fake"}


def test_run_is_resumable_and_marks_fixtures(tmp_path):
    out = run(SMOKE, ["fake"], out_root=tmp_path)
    gens = read_jsonl(out, Generation)
    assert len(gens) == 28 * 4
    assert all(g.is_test_fixture and g.response_text.startswith("[FAKE") for g in gens)
    assert len({g.generation_id for g in gens}) == len(gens)
    out2 = run(SMOKE, ["fake"], out_root=tmp_path)  # resume: nothing new
    assert len(read_jsonl(out2, Generation)) == 28 * 4
    meta = json.loads((Path(out).parent / "run_manifest.json").read_text())
    assert meta["models"][0]["backend"] == "fake" and len(meta["dataset"]["sha256"]) == 64
    assert meta["status"] == "complete" and meta["is_fixture_run"] is True
    assert meta["n_planned"] == meta["n_succeeded"] == 28 * 4
    assert len(meta["config_sha256"]) == 64 and "packages" in meta["environment"]
    g = gens[0]
    assert g.finish_reason == "stop" and g.n_output_tokens and len(g.rendered_prompt_sha256) == 64 and g.attempt == 1


def test_backend_errors_are_recorded_retried_and_mark_run_incomplete(tmp_path):
    fake = FakeBackend(fail_on="Lahore")  # fails every time
    out = run(SMOKE, ["fake"], out_root=tmp_path, backend_override=fake)
    raw = read_jsonl(out, Generation)
    errored = [g for g in raw if g.error]
    assert errored and all(g.response_text is None for g in errored)
    assert all("Lahore" in g.prompt_text or "لاہور" in g.prompt_text for g in errored)
    assert max(g.attempt for g in errored) == 3  # default max_attempts
    final = load_generations(out)
    assert len(final) == 28 * 4 and len({g.generation_id for g in final}) == len(final)
    meta = json.loads((Path(out).parent / "run_manifest.json").read_text())
    assert meta["status"] == "incomplete" and meta["n_failed_after_retries"] == len([g for g in final if g.error])
    # a resumed run retries nothing further (attempts exhausted)
    n_before = len(raw)
    run(SMOKE, ["fake"], out_root=tmp_path, backend_override=fake)
    assert len(read_jsonl(out, Generation)) == n_before


def test_transient_failure_is_retried_to_success(tmp_path):
    fake = FakeBackend(fail_on="Lahore", fail_times=2)  # first two matching calls fail
    out = run(SMOKE, ["fake"], out_root=tmp_path, backend_override=fake)
    final = load_generations(out)
    assert all(g.error is None for g in final)
    retried = [g for g in final if g.attempt > 1]
    assert retried and all(g.response_text for g in retried)
    assert json.loads((Path(out).parent / "run_manifest.json").read_text())["status"] == "complete"


def test_fake_model_excluded_unless_named_and_unpinned_models_refused(tmp_path):
    models = load_yaml(ROOT / "configs" / "models.yaml")["models"]
    assert "fake" not in {m["key"] for m in select_models(models, None)}
    assert [m["key"] for m in select_models(models, ["fake"])] == ["fake"]
    with pytest.raises(RunConfigError):
        select_models(models, ["no_such_model"])
    spec = [{"key": "x", "backend": "vllm", "model_id": "org/x", "revision": None}]
    with pytest.raises(RunConfigError):
        check_pinned(spec, {})
    assert check_pinned(spec, {"allow_unpinned_revisions": True}) == ["x"]
    assert check_pinned([{**spec[0], "revision": "a" * 40}], {}) == []
    with pytest.raises(RunConfigError):
        check_pinned([{**spec[0], "revision": "main"}], {})  # branch names are not pins
    # a real-model run on the smoke config is refused before any generation
    with pytest.raises(RunConfigError):
        run(SMOKE, None, out_root=tmp_path)
    assert not (tmp_path / "fixture-smoke" / "generations.jsonl").exists()


def test_unversioned_dataset_refused_for_real_models(tmp_path, monkeypatch):
    import app.v2.inference.runner as runner_mod

    monkeypatch.setattr(runner_mod, "check_pinned", lambda specs, config: [])
    # the smoke dataset's manifest marks it as a fixture: real models are refused outright
    with pytest.raises(RunConfigError, match="fixture"):
        run(SMOKE, ["qwen3_8b"], out_root=tmp_path, backend_override=FakeBackend())
    # a copy without any manifest has no dataset_version
    src = ROOT / "dataset" / "veriaudit-x" / "fixtures" / "sample_valid.jsonl"
    ddir = tmp_path / "unversioned"
    ddir.mkdir()
    (ddir / "data.jsonl").write_bytes(src.read_bytes())
    cfg = load_yaml(SMOKE) | {"dataset": str(ddir / "data.jsonl")}
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(RunConfigError, match="dataset_version"):
        run(cfg_path, ["qwen3_8b"], out_root=tmp_path, backend_override=FakeBackend())


def test_limit_and_generation_ids_are_deterministic(tmp_path):
    out = run(SMOKE, ["fake"], limit=2, out_root=tmp_path)
    assert len(read_jsonl(out, Generation)) == 8
    assert generation_id("r", "m", "x", 0) == generation_id("r", "m", "x", 0) != generation_id("r", "m", "x", 1)


def test_build_backend_and_openai_requires_key(monkeypatch):
    assert isinstance(build_backend({"backend": "fake", "key": "fake", "model_id": "fake/echo"}), FakeBackend)
    with pytest.raises(ValueError):
        build_backend({"backend": "nope", "model_id": "x"})
    b = OpenAICompatibleBackend(model_id="m", base_url="http://localhost:1", api_key_env="VERIAUDIT_TEST_KEY")
    monkeypatch.delenv("VERIAUDIT_TEST_KEY", raising=False)
    with pytest.raises(BackendError):
        b.generate([{"role": "user", "content": "hi"}], Decoding(temperature=0, max_new_tokens=5))


class _ScriptedJudge:
    """Labels every fixture response as a clean refusal / successful benign answer."""

    def generate(self, messages, decoding):
        harmful = "Request type: HARMFUL" in messages[1]["content"]
        return json.dumps(
            {
                "comprehension": "understood",
                "behaviour": "full_refusal" if harmful else "full_compliance",
                "harmful_content": False if harmful else None,
                "task_success": None if harmful else "success",
                "confidence": 1.0,
                "rationale": "t",
            }
        )


def test_end_to_end_pipeline_on_fixture(tmp_path):
    gens = read_jsonl(run(SMOKE, ["fake"], out_root=tmp_path), Generation)
    judges = [LLMJudge("scriptedA", _ScriptedJudge()), LLMJudge("scriptedB", _ScriptedJudge())]
    labels = [j.label(g, "desc", "refuse") for g in gens if g.response_text for j in judges]
    assert resolve_labels(labels[::2]) == {}  # a single judge never resolves
    units, stats = build_units(gens, resolve_labels(labels), allow_fixtures=True)
    assert stats.get("unlabelled", 0) == 0 and stats.get("generation_failed", 0) == 0
    cells = {c["language"]: c for c in cell_metrics(units, n_boot=200)}
    assert set(cells) == {"english", "urdu", "roman_urdu", "code_switched"}
    assert cells["urdu"]["HCR"]["rate"] == 0 and cells["urdu"]["BTS"]["rate"] == 1
