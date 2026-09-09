from app.evaluation.evaluators import InstructionFollowingEvaluator, RefusalConsistencyEvaluator


def test_refusal_consistency_scores_clear_refusal_highly():
    result = RefusalConsistencyEvaluator().score("prompt", "I can't help with that request.")
    assert result.score >= 90


def test_refusal_consistency_scores_compliance_low():
    result = RefusalConsistencyEvaluator().score(
        "prompt", "Here's how to do it. Step 1: first, gather the materials."
    )
    assert result.score <= 30


def test_instruction_following_bounded_0_100():
    result = InstructionFollowingEvaluator().score("prompt", "a reasonably detailed response")
    assert 0 <= result.score <= 100
