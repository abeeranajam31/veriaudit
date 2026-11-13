"""Judge runner: resumable labelling, unparseable outputs recorded, family and pinning checks."""

import json

import pytest

from app.v2.judges.run_judge import JudgeConfigError, check_judge, judge_generations
from app.v2.records import Decoding, Generation


def gen(i, stype="harmful", error=None):
    return Generation(
        generation_id=f"g{i}", run_id="r", model_key="m", model_id="org/m", backend="fake", record_id=f"R{i}", scenario_id=f"S{i}",
        intent_id=f"S{i}-H", scenario_type=stype, language="urdu", transformation_type="translation", prompt_text=f"prompt-{i}",
        decoding=Decoding(temperature=0.0, max_new_tokens=10), sample_index=-1, response_text=None if error else "resp", error=error,
    )  # fmt: skip


GOOD = '{"comprehension": "understood", "behaviour": "full_refusal", "harmful_content": false, "task_success": null, "confidence": 0.9, "rationale": "x"}'


def test_labels_resumes_and_records_unparseable(tmp_path):
    gens = [gen(1), gen(2), gen(3, error="oom")]
    records = {f"R{i}": {"intent_description": "d", "expected_behavior": "refuse"} for i in range(1, 4)}
    calls = []

    def batch(msgs, d):
        calls.append(len(msgs))
        # g2 always returns reasoning text with stray braces and no valid answer
        return [GOOD if "prompt-1" in str(m) else "thinking {about it} ... no answer" for m in msgs]

    out = tmp_path / "labels.jsonl"
    c = judge_generations(gens, records, "j", batch, out)
    assert c["labelled"] == 1 and c["unparseable"] == 1 and c["not_judgeable_errored"] == 1
    lab = json.loads(out.read_text().splitlines()[0])
    assert lab["labeler_id"].startswith("j@") and lab["label_source"] == "ai_judge"
    assert "g2" in (tmp_path / "failures" / "labels.jsonl").read_text()
    calls.clear()
    c2 = judge_generations(gens, records, "j", lambda m, d: [GOOD] * len(m), out)  # resume: only g2 is re-tried
    assert c2["labelled"] == 1 and c2["skipped_already_labelled"] == 1


def test_reasoning_preamble_with_braces_is_parsed(tmp_path):
    text = "Let me think {step one} and {step two}.\nFinal: " + GOOD
    c = judge_generations([gen(1)], {"R1": {"intent_description": "d", "expected_behavior": "refuse"}}, "j", lambda m, d: [text], tmp_path / "o.jsonl")
    assert c["labelled"] == 1


def test_judge_checks():
    manifest = [{"model_id": "Qwen/Qwen3-8B", "confirmatory": True}, {"model_id": "google/gemma-4-E4B-it", "confirmatory": True}]
    with pytest.raises(JudgeConfigError, match="not pinned"):
        check_judge({"key": "a", "backend": "vllm", "model_id": "openai/gpt-oss-120b", "revision": None}, manifest)
    with pytest.raises(JudgeConfigError, match="under test"):
        check_judge({"key": "b", "backend": "vllm", "model_id": "google/gemma-3-27b-it", "revision": "a" * 40}, manifest)
    check_judge({"key": "c", "backend": "vllm", "model_id": "openai/gpt-oss-120b", "revision": "a" * 40}, manifest)


def test_cli_on_fixture_run(tmp_path):
    """End to end through main(): run manifest -> dataset (hash-checked) -> judge -> label file."""
    from pathlib import Path

    from app.v2.inference.runner import run
    from app.v2.judges import run_judge

    repo = Path(__file__).resolve().parents[2]
    gens_file = run(repo / "configs/experiments/fixture_smoke.yaml", ["fake"], out_root=tmp_path)
    judges = tmp_path / "judges.yaml"
    judges.write_text("judges:\n  - key: fakejudge\n    backend: fake\n    model_id: fake/echo\n")
    out = tmp_path / "labels.jsonl"
    assert run_judge.main(["--run", str(gens_file.parent), "--judge", "fakejudge", "--judges", str(judges), "--out", str(out)]) == 0
    # the echo backend never returns JSON: nothing is labelled, everything is recorded as unparseable
    assert not out.exists() or out.read_text() == ""
    assert (tmp_path / "failures" / "labels.jsonl").read_text().count("fakejudge@") > 0


def test_unambiguous_variants_are_accepted_and_raw_output_is_kept(tmp_path):
    variant = GOOD.replace('"understood"', '"Fully understood"').replace('"full_refusal"', '"full-refusal"')
    junk = GOOD.replace('"understood"', '"kind of got it"')
    records = {f"R{i}": {"intent_description": "d", "expected_behavior": "refuse"} for i in (1, 2)}
    c = judge_generations([gen(1), gen(2)], records, "j", lambda m, d: [variant if "prompt-1" in str(m) else junk for m in m], tmp_path / "o.jsonl")
    assert c["labelled"] == 1 and c["unparseable"] == 1
    fail = json.loads((tmp_path / "failures" / "o.jsonl").read_text())
    assert "kind of got it" in fail["raw_output"]
