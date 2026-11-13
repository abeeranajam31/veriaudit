# Amendments A6 and A7, in plain language

Both amendments were written on 2026-11-13, before any translation, inference or annotation. Neither
was chosen by looking at data, because there is none yet. Each needs your decision: accept it, or
reject it with a reason. Record the decision in the amendment log (§15 of
`docs/v2/research_protocol.md`).

## A6: the main test becomes a paired t-test

**What the study measures.** For each model and each non-English form, every scenario gets a share:
how many of the 3 sampled answers were harmful (0, ⅓, ⅔ or 1). The gap for that scenario is the
share in, say, Roman Urdu minus the share in English. CLSG is the **average** of those 200 gaps.

**What was wrong.** The old main test (Wilcoxon signed-rank) does not ask "is the average gap zero?"
It asks something closer to "do positive gaps outnumber negative ones, once zeros are thrown away?".
Most gaps here are exactly zero, because most prompts are refused in both languages. With so many
zeros the two questions can give **opposite answers**.

An example: 9% of scenarios go from 0 to ⅔ harmful in Urdu, and 6% go from fully harmful to 0. The
average gap is exactly zero. In simulation, the old test still reported a significant gap in 25.5%
of studies, where it should be 5%. In other set-ups with a real positive gap, it sometimes reported
a significant gap in the wrong direction. A reviewer who knows statistics would catch this.

**What A6 does.**

- The paired t-test directly tests "is the average gap zero?", which is exactly CLSG. In 11
  simulated "no gap" situations it raised false alarms at most 5.3% of the time at α = .05, and at
  the expected rate after correcting for the 12 tests.
- The confidence interval for CLSG becomes the matching t interval. It is honestly labelled
  *approximate*: in simulation it covered the truth 92–97% of the time instead of exactly 95%.
- The signed-rank test is still reported as a descriptive extra, never as evidence about CLSG.

**What it costs.** Almost nothing. Power is the same or better in every scenario simulated except
one very rare-outcome case: 0.17 versus 0.19 for 0.5% → 2%.

**Recommendation: accept A6.** If you reject it, the paper's main test would measure a different
quantity from the one the paper reports, and that is a fatal flaw.

## A7: how the calibration pilot decides whether 200 scenarios are enough

**The question.** Can 200 scenarios detect a 10-percentage-point gap (the smallest gap the protocol
cares about), with 80% probability, after correcting for 12 tests? The answer depends on facts we do
not know yet:

- how often each model gives harmful answers in English (the **base rate**);
- how much prompts differ from each other;
- whether a model's 3 sampled answers to one prompt are near-copies of each other.

The pilot measures these, mostly from English prompts.

**What A7 fixes in advance.**

1. **The quantity.** For every confirmatory model and both families (H1 harmful compliance, H2
   over-refusal), the pilot computes the **minimum detectable effect (MDE)**: the smallest gap the
   study would detect with 80% probability.
2. **A cautious assumption.** The pilot cannot measure how much of a scenario's behaviour carries
   over from English to Urdu, because it has only one harmful scenario in Urdu. So it assumes the
   worst case for a paired design: nothing carries over. This overstates the MDE, never understates
   it.
3. **An extra margin.** The pilot has only about 41 English scenarios per model, so the decision
   uses a pessimistic (90th-percentile) estimate of prompt-to-prompt variation.
4. **The rule.**
   - If every MDE is ≤ 10 points under the pessimistic estimate: **adequate**.
   - If every MDE is ≤ 10 only at the normal estimate: **adequate with a stated limitation**.
   - Otherwise: **not adequate**, and you choose between pre-registering the MDE, 5 samples per
     prompt, or more scenarios, by amendment **before** the main study.
   - Not allowed after seeing the pilot: changing the test, dropping a model, one-sided tests, or
     pooling forms.

**Statistical implications you should know before accepting.** The conservative MDE grows with the
base rate. A gap of 10 points is harder to detect around 30% than around 5%, because answers vary
more there:

| English base rate | MDE (pp) at low prompt variation | at high prompt variation |
|---|---|---|
| 1% | 3.6 | 5.0 |
| 5% | 5.9 | 8.1 |
| 10% | 7.6 | 10.3 |
| 20% | 9.6 | 12.9 |
| 30% | 10.7 | 14.3 |

(`mde_paired_t_conservative`, n = 200, α = .05/12, 80% power. These are planning numbers, not
results.)

So:

- **A model whose English harmful-compliance or over-refusal rate is about 15–20% or more will
  probably fail the rule.** Over-refusal (H2) is the family most at risk. An outcome of
  **"not adequate" for some cells is quite likely.** That is not a failure of the study; it is the
  honest answer.
- If that happens, the cheap and defensible response is **option 1**: pre-register the MDEs and
  report every non-significant cell with them, for example "no gap larger than 13 points".
  - **Option 3 (more scenarios)** is expensive. An MDE of 13 points needs about
    200 × (13/10)² ≈ 340 scenarios, which is roughly 840 more translated variants plus reviews.
  - **Option 2 (5 samples)** helps only if a model's samples disagree with each other often.
- Because the rule is conservative, "not adequate" can be triggered even when realistic power is
  fine. The trade-off is deliberate: a reviewer cannot say you picked the rule after seeing the data
  or made it easy to pass.

**The alternative you could choose instead (only now, before the pilot).** Base the rule on the
normal rather than the pessimistic estimate, so that "adequate" is whenever `mde_pp_conservative` ≤
10. That is less cautious, and I don't recommend it: with only ~41 pilot scenarios the normal
estimate is noisy.

**Recommendation: accept A7 as written.** Expect "adequate with limitation" or "not adequate" for
some H2 cells, and plan for option 1 in that case. All three outcomes lead to a publishable study.

## How to record your decision

Add the decision to the A6 and A7 rows in §15 of the protocol, or reply "accept A6 and A7" and I
will record it with today's date. Example wording for the log:
`Accepted by the PI on <date>, before any data collection.`
