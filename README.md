# VeriAudit

**Measuring what multilingual AI safety evaluations actually measure.**

When a language model looks less safe in a lower-resource language, there are three possible
reasons:

1. it produces harmful content;
2. it fails to understand the request;
3. it is being misjudged by an evaluator built for English.

VeriAudit is an independent research project, with an open-source evaluation framework, that
separates these three explanations. It covers English, Urdu (Perso-Arabic script), Roman Urdu and
Urdu–English code-switching.

**Paper:** [Comprehension, Not Only Compliance (PDF)](paper/v01_reanalysis/main.pdf) ·
**Website:** [veriiaudit.vercel.app](https://veriiaudit.vercel.app) ·
**Results:** [`results/`](results/) ·
**Protocol:** [`docs/v2/research_protocol.md`](docs/v2/research_protocol.md)

---

## Key findings

**1. Refusal detection collapses outside English.**
An English-pattern refusal detector recognised 92% of English refusals but **0 of 40** Urdu-script
refusals, and only 16–19% of Roman Urdu and code-switched ones. Scored that way, the same responses
show safety gaps of 42.5–70 percentage points instead of 10–40.
([`results/v1_reconstruction/`](results/v1_reconstruction/))

**2. Denominator choices change the headline gap.**
Count only genuine harmful compliance, over every scenario pair, and Qwen3-8B's Roman Urdu gap falls
from **39.5 to 26.7 points**. It is then no longer significant after Holm correction. Count the same
non-scoreable outputs as unsafe instead, and the gap rises to 56.7. The direction of every gap is
stable; its size and significance are not.

**3. Language generation and language understanding are separate problems.**
Aya Expanse 8B answers **71%** of Roman Urdu prompts and 65% of code-switched prompts in Hindi
(Devanagari) script, reproducing the original evaluation. Qwen3-8B falls into repetition loops in
Roman Urdu. Script drift and comprehension failure change what a safety judge has to read.

**4. Multi-model evaluation with independent automated judges** (exploratory).
Three open-weight models were evaluated: Qwen3-8B, Aya Expanse 8B and Qwen3.5-9B, with 1,440
generations in total (greedy decoding plus three samples per prompt). Each response was labelled by
two judges from model families outside the panel, Mistral-Nemo-12B and Granite-3.3-8B.

| Model | Form | Gap vs English, judge A (pp, 95% CI) | Gap vs English, judge B (pp, 95% CI) |
|---|---|---|---|
| Aya Expanse 8B | Urdu script | +12.2 [3.9, 20.5] | +11.1 [2.2, 20.1] |
| Qwen3-8B | Roman Urdu | +10.1 [2.1, 18.2] | +20.4 [3.2, 37.6] |
| Qwen3.5-9B | all forms | +1.1 to +2.2 | 0.0 to +2.8 |

- Both judges find no harmful compliance in English, and the same direction of gap for Aya Expanse
  in Urdu script and Qwen3-8B in Roman Urdu.
- The judges agree on *whether* a response is harmful 96% of the time (κ = 0.44), but on *how* a
  model refused only 50% of the time. Evaluator reliability is therefore itself an open question,
  and human validation of these labels is under way.

Details: [`results/v2/exploratory/v01-panel/`](results/v2/exploratory/v01-panel/).

---

## What is in this repository

| Component | Where |
|---|---|
| Paper (re-analysis of the original evaluation) | [`paper/v01_reanalysis/`](paper/v01_reanalysis/) |
| Exact reproduction of all 191 published numbers from raw outputs | [`research/v1_reconstruction/`](research/v1_reconstruction/), [`results/v1_reconstruction/`](results/v1_reconstruction/) |
| Pre-registered study protocol, with a dated amendment log | [`docs/v2/research_protocol.md`](docs/v2/research_protocol.md) |
| Statistical validation (11 null scenarios × 20,000 simulations; the primary test chosen by simulation) | [`docs/v2/statistical_validation_v2.md`](docs/v2/statistical_validation_v2.md) |
| VeriAudit-X dataset framework: schema, validation, splits, 200-scenario design | [`backend/app/veriaudit_x/`](backend/app/veriaudit_x/), [`docs/v2/`](docs/v2/) |
| Evaluation pipeline: pinned-model runners, two-judge labelling, analysis | [`backend/app/v2/`](backend/app/v2/), [`configs/`](configs/), [`research/`](research/) |
| Human translation, review and annotation workflow (independence enforced in code) | [`docs/v2/translation_guide.md`](docs/v2/translation_guide.md), [`backend/app/v2/human_labels.py`](backend/app/v2/human_labels.py) |
| Integrity safeguards, verified by replaying 13 failure scenarios | [`docs/v2/safeguard_verification.md`](docs/v2/safeguard_verification.md) |
| Interactive website | [`frontend/`](frontend/) |

Documentation index: [`docs/v2/README.md`](docs/v2/README.md).

## Reproduce

```bash
cd backend && pip install -r requirements.txt -r requirements-v2.txt pytest && python -m pytest -q   # test suite
PYTHONPATH=backend python research/v1_reconstruction/reconstruct.py   # prints 191/191 matched
PYTHONPATH=backend python research/stats_validation/validate_v2.py    # statistical validation (~5 min)
```

The multi-model run uses free Kaggle GPUs:
[`research/inference/kaggle_exploratory_v01.ipynb`](research/inference/kaggle_exploratory_v01.ipynb).
Model revisions are pinned in [`configs/`](configs/), and every run records hashes of its dataset,
config and outputs.

## Status and scope

| Item | Status |
|---|---|
| Findings 1–3 | 30 harmful scenarios in four forms; two models in the original evaluation |
| Finding 4 | Exploratory. Labels are from automated judges and are being validated by human annotators |
| VeriAudit-X | A 200-scenario benchmark with matched benign contrasts, translated and independently reviewed by human bilingual annotators. In development |
| Raw model responses that may contain harmful text | Released only where needed for reproduction |

## Citation

```bibtex
@misc{najam2026veriaudit,
  author = {Najam, Abeera},
  title  = {VeriAudit: Measuring What Multilingual AI Safety Evaluations Actually Measure},
  year   = {2026},
  url    = {https://github.com/abeeranajam31/veriaudit}
}
```

## Licence and contact

[MIT](LICENSE). **Abeera Najam**, Lead Researcher ·
[veriiaudit@gmail.com](mailto:veriiaudit@gmail.com) ·
[GitHub](https://github.com/abeeranajam31) ·
[LinkedIn](https://linkedin.com/in/abeeranajam)
