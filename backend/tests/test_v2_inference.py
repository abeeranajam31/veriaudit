"""CPU tests of the inference pipeline with the FakeBackend (outputs are test fixtures, never results)."""

import json
from pathlib import Path

import pytest

from app.v2.inference.backends import BackendError, FakeBackend, OpenAICompatibleBackend, build_backend
from app.v2.inference.runner import ROOT, generation_id, load_yaml, plan, run
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
    meta = json.loads((Path(out).parent / "run_metadata.json").read_text())
    assert meta["models"][0]["backend"] == "fake" and len(meta["dataset_sha256"]) == 64


def test_backend_errors_are_recorded_not_raised(tmp_path):
    fake = FakeBackend(fail_on="Lahore")
    out = run(SMOKE, ["fake"], out_root=tmp_path, backend_override=fake)
    gens = read_jsonl(out, Generation)
    errored = [g for g in gens if g.error]
    assert errored and all(g.response_text is None for g in errored)
    assert all("Lahore" in g.prompt_text or "لاہور" in g.prompt_text for g in errored)


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
    judge = LLMJudge("scripted", _ScriptedJudge())
    labels = [judge.label(g, "desc", "refuse") for g in gens if g.response_text]
    units, stats = build_units(gens, resolve_labels(labels), allow_fixtures=True)
    assert stats.get("unlabelled", 0) == 0 and stats.get("generation_failed", 0) == 0
    cells = {c["language"]: c for c in cell_metrics(units, n_boot=200)}
    assert set(cells) == {"english", "urdu", "roman_urdu", "code_switched"}
    assert cells["urdu"]["HCR"]["rate"] == 0 and cells["urdu"]["BTS"]["rate"] == 1
