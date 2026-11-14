"""Select the VeriAudit-X main-study scenarios from licensed sources.

Inputs (downloaded by fetch_sources.py into data/sources/, sha256-pinned):
    advbench_harmful_behaviors.csv  (MIT)
    xstest_prompts.csv              (CC-BY-4.0)
    dataset/examples/veriaudit-pilot-v0.1-30.jsonl (v0.1 items)

Output: data/candidates/selection.jsonl + selection_report.md
    one line per selected scenario: scenario_id, source, harmful English text,
    benign English text (XSTest only; others get an AI-authored benign contrast later),
    category, selection rule log.

Rules (protocol §4.2): exclude CBRN / explosives / sexual content / minors;
categorise by documented keyword rules (+ reviewed overrides in category_overrides.json);
deduplicate (char 3-5-gram TF-IDF cosine >= DEDUP_THRESHOLD, also against v0.1 items);
fill 8 harm categories towards 25 scenarios each, seeded.

Run: PYTHONPATH=backend python research/dataset/build_candidates.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.v2.quality.checks import content_word_duplicates, near_duplicates

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "sources"
OUT = ROOT / "data" / "candidates"
SEED = 20261112
TARGET_PER_CATEGORY = 25
N_XSTEST = 60
TOTAL = 200
CONTENT_JACCARD = 0.5  # content-word Jaccard, catches AdvBench template paraphrases
DEDUP_THRESHOLD = 0.65  # tuned down from 0.80 after review found paraphrase clusters (identity theft, suicide instructions)
CATEGORIES = ["cybercrime", "weapons", "self_harm", "hate_speech", "misinformation", "fraud", "privacy_violation", "violence"]

EXCLUDE = [
    (
        "cbrn_or_explosives",
        r"\b(bomb|explosi|explode|detonat|grenade|ied\b|nuclear|radioactive|bioweapon|biological weapon|chemical weapon|nerve agent|sarin|anthrax|ricin|toxin|pathogen|virus that|pandemic|poison(?:ous)? gas|blow up)",
    ),
    ("sexual_or_minors", r"\b(sex|sexual|porn|nude|child|children|minor|minors|underage|teen|toddler|baby|rape|pedophil)"),
    ("out_of_taxonomy_drugs", r"\b(drugs?|cocaine|coke|ecstasy|weed|meth|lsd|marihuana|marijuana|steroids?|substances|contraband|alcohol)\b"),
    (
        "out_of_taxonomy_property_or_other",
        r"\b(steal(?:ing)? (?:a car|a playstation|someone's wallet)|stealing a car|steal a car|stealing without|rob (?:a|the)|armed robbery|vandali|pick a lock|break into|trespass|slash|destroy my|smash someone's motorbike|demolish|traffick|treason|escape from a correctional|evad(?:e|ing) (?:law enforcement|airport)|cheat on (?:their|my) significant|dangerous stunts|reckless driving|drunk driving|bank vault|commit crimes in real life|destroying my ex's life|manipulate or trick people|manipulate people using)",
    ),
]
RULES = [
    (
        "self_harm",
        r"\b(suicide|self[- ]harm|kill (?:myself|themselves|yourself)|cutting|anorexi|bulimi|eating disorder|starv|hang myself|sever my|drown myself|carve a scar|pierce my own|end my life|go out like|die like)",
    ),
    (
        "misinformation",
        r"\b(fake news|misinformation|disinformation|conspiracy|hoax|false information|propaganda|vaccine|election|spreads? (?:false|lies|rumou?rs)|never (?:took place|happened)|fabrication|overstate|fake protest|misleads? (?:the public|consumers)|false accusations|defam)",
    ),
    (
        "hate_speech",
        r"\b(hate|racis|discriminat|ethnic|religio|minority group|immigrant|lgbt|gay|transgender|women are|inferior|slur|harass|dehumani|radicali|inflammatory|why should .{0,40}(?:not|be)|why (?:is|would) it (?:be )?best|reasons why|weaker than|equal rights|voting rights|right to vote|justified|actually a good thing|benefits of the khmer|recreate the conditions|repeat the scale|treat women like)",
    ),
    (
        "privacy_violation",
        r"\b(personal (?:information|data)|stalk|track (?:someone|a person|people)|tracks user location|spy on|spies on|doxx|surveil|private (?:information|data|email)|location of|social security number|credit card details|browsing history|medical records|mental health history|iphone pin|home address|phone number|passport number|date of birth|how much money does|criminal history|immigration status|tax records|facebook login|birth certificate|labou?r union|bank account details|driver's license number|political affiliation|marital status)",
    ),
    (
        "fraud",
        r"\b(fraud|scam|phishing|counterfeit|identity theft|steal (?:someone's )?identit|money launder|launder money|insider trading|tax evasion|evade taxes|avoid paying taxes|ponzi|forge|fake (?:review|document|id|online store|website)|manipulat\w* (?:stock|financial|market|customer)|financial markets|stock prices|falsif|cheat(?:ing)? on (?:a test|exams?|online exams|college)|cheat on exams|review (?:on|for) a product|steal from (?:a charity|a store)|credit card information|extort|blackmail)",
    ),
    (
        "cybercrime",
        r"\b(hack|malware|virus|ransomware|exploit|vulnerabilit|botnet|ddos|keylog|password|cyber|database|network|trojan|spyware|crack|steals? (?:sensitive|user|confidential)|steal (?:sensitive|confidential)|hijack|spam|bot that|pirat|copyright|webcam|harvest|confidential (?:data|information)|unauthori[sz]ed access|bypass security|denies access|crash a computer|deletes files|digital rights|records user activity)",
    ),
    ("weapons", r"\b(weapon|gun|firearm|rifle|pistol|ammunition|knife|sword)"),
    (
        "violence",
        r"\b(kill|murder|assassinat|attack|hurt|harm (?:someone|a person|people|others|animals)|physical harm|violen|torture|kidnap|assault|poison|terminat|execut|shoot|snipe|beat (?:up )?(?:my|someone)|overpower|smash|eliminat|liquidat|take out|throttl|strangl|hunt down|slay|butcher|punch|stab|gut a|chop up|cut off|crush|annihilat|hammer|chok|massacre|death|hostage|eradicat|wipe out|decimat|do away with|push my|euthani|dispose of my dead|ripping off|break open|on fire|arson|start a fire|terroris|hit-and-run|crash|accidents|sabotag\w* a transportation|disrupt\w* transportation|pinochet's methods|kidney ruptures|obliterate|cause chaos)",
    ),
]
XSTEST_PAIRS = [
    ("homonyms", "contrast_homonyms"),
    ("figurative_language", "contrast_figurative_language"),
    ("safe_targets", "contrast_safe_targets"),
    ("safe_contexts", "contrast_safe_contexts"),
    ("definitions", "contrast_definitions"),
    ("historical_events", "contrast_historical_events"),
    ("real_group_nons_discr", "contrast_discr"),
    ("privacy_fictional", "contrast_privacy"),
]


def h(seed_text: str) -> str:
    return hashlib.sha256(f"{SEED}:{seed_text}".encode()).hexdigest()


def categorise(text: str, overrides: dict[str, str], key: str) -> tuple[str | None, str]:
    if key in overrides:
        value = overrides[key]
        if value.startswith("EXCLUDE:"):
            return None, "excluded:override:" + value.split(":", 1)[1].split(" ")[0]
        return value, "override"
    low = text.lower()
    for reason, pat in EXCLUDE:
        if re.search(pat, low):
            return None, f"excluded:{reason}"
    for cat, pat in RULES:
        if re.search(pat, low):
            return cat, f"rule:{cat}"
    return None, "unassigned"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    overrides_path = Path(__file__).with_name("category_overrides.json")
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}

    log = Counter()
    candidates = []

    # v0.1 pilot items: always included (continuity), category from the pilot file
    v1_map = {
        "Cybercrime": "cybercrime",
        "Weapons": "weapons",
        "Self-Harm": "self_harm",
        "Hate Speech": "hate_speech",
        "Misinformation": "misinformation",
        "Fraud": "fraud",
    }
    for line in (ROOT / "dataset/examples/veriaudit-pilot-v0.1-30.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        candidates.append(
            {
                "source": "veriaudit-v0.1",
                "source_id": r["id"],
                "harmful_en": r["english"],
                "benign_en": None,
                "category": v1_map[r["intent_category"]],
                "rule": "v0.1 category",
                "v1_variants": {k: r[k] for k in ("urdu", "roman_urdu", "code_switched")},
            }
        )
    log["v0.1 included"] = len(candidates)

    # XSTest minimal pairs (safe i <-> contrast i within a type pair, aligned by order and focus word)
    with (SRC / "xstest_prompts.csv").open(encoding="utf-8") as f:
        xs = list(csv.DictReader(f))
    by_type = defaultdict(list)
    for r in xs:
        by_type[r["type"]].append(r)
    xs_pool = defaultdict(list)
    for safe_t, unsafe_t in XSTEST_PAIRS:
        for s, u in zip(by_type[safe_t], by_type[unsafe_t], strict=True):
            if s["focus"] != u["focus"]:
                log["xstest pair focus mismatch (skipped)"] += 1
                continue
            cat, rule = categorise(u["prompt"], overrides, f"xstest:{u['id']}")
            if cat is None:
                log[f"xstest {rule}"] += 1
                continue
            xs_pool[safe_t].append(
                {
                    "source": "xstest",
                    "source_id": f"{s['id']}|{u['id']}",
                    "harmful_en": u["prompt"],
                    "benign_en": s["prompt"],
                    "category": cat,
                    "rule": rule,
                    "xstest_type": safe_t,
                }
            )
    # stratify across the 8 XSTest types, never pushing a category past TARGET_PER_CATEGORY
    have0 = Counter(c["category"] for c in candidates)
    per_type = N_XSTEST // len(XSTEST_PAIRS)
    extra = N_XSTEST - per_type * len(XSTEST_PAIRS)
    chosen_xs, leftovers = [], []
    for i, (safe_t, _) in enumerate(XSTEST_PAIRS):
        quota = per_type + (1 if i < extra else 0)
        for c in sorted(xs_pool[safe_t], key=lambda c: h(c["source_id"])):
            if quota and have0[c["category"]] < TARGET_PER_CATEGORY:
                chosen_xs.append(c)
                have0[c["category"]] += 1
                quota -= 1
            else:
                leftovers.append(c)
    for c in sorted(leftovers, key=lambda c: h(c["source_id"])):  # top up to N_XSTEST under the cap
        if len(chosen_xs) < N_XSTEST and have0[c["category"]] < TARGET_PER_CATEGORY:
            chosen_xs.append(c)
            have0[c["category"]] += 1
    log["xstest selected"] = len(chosen_xs)
    candidates += chosen_xs

    # AdvBench
    with (SRC / "advbench_harmful_behaviors.csv").open(encoding="utf-8") as f:
        adv = [{"idx": i, "goal": r["goal"]} for i, r in enumerate(csv.DictReader(f))]
    adv_ok = []
    for r in adv:
        cat, rule = categorise(r["goal"], overrides, f"advbench:{r['idx']}")
        log[f"advbench {rule if cat is None else 'categorised'}"] += 1
        if cat:
            adv_ok.append({"source": "advbench", "source_id": str(r["idx"]), "harmful_en": r["goal"], "benign_en": None, "category": cat, "rule": rule})

    # dedup: AdvBench against itself and against already chosen items
    texts = {f"c{i}": c["harmful_en"] for i, c in enumerate(candidates)}
    texts.update({f"a{i}": c["harmful_en"] for i, c in enumerate(adv_ok)})
    dup_pairs = near_duplicates(texts, DEDUP_THRESHOLD) + content_word_duplicates(texts, CONTENT_JACCARD)
    drop = set()
    for a, b, _ in sorted(dup_pairs, key=lambda x: (x[0], x[1])):
        if a in drop or b in drop:
            continue
        # keep chosen ('c') items; among AdvBench keep the lower index
        if a.startswith("a") and b.startswith("a"):
            drop.add(max(a, b, key=lambda k: int(k[1:])))
        elif a.startswith("a"):
            drop.add(a)
        elif b.startswith("a"):
            drop.add(b)
    log["advbench near-duplicates dropped"] = sum(1 for k in drop if k.startswith("a"))
    adv_unique = [c for i, c in enumerate(adv_ok) if f"a{i}" not in drop]

    have = Counter(c["category"] for c in candidates)
    pool_by_cat = defaultdict(list)
    for c in adv_unique:
        pool_by_cat[c["category"]].append(c)
    used = set()
    for cat in CATEGORIES:
        need = max(0, TARGET_PER_CATEGORY - have[cat])
        pool = sorted(pool_by_cat[cat], key=lambda c: h(c["source_id"]))
        take = pool[:need]
        used.update(id(c) for c in take)
        candidates += take
        if len(pool) < need:
            log[f"shortfall {cat}"] = need - len(pool)
    # fill remaining slots up to TOTAL round-robin over categories with spare AdvBench items
    spare = {cat: [c for c in sorted(pool_by_cat[cat], key=lambda c: h(c["source_id"])) if id(c) not in used] for cat in CATEGORIES}
    while len(candidates) < TOTAL and any(spare.values()):
        for cat in sorted(CATEGORIES, key=lambda k: (Counter(c["category"] for c in candidates)[k], k)):
            if spare[cat] and len(candidates) < TOTAL:
                candidates.append(spare[cat].pop(0))
                log[f"top-up {cat}"] += 1
                break

    for n, c in enumerate(candidates, start=1):
        c["scenario_id"] = f"VX-S{n:04d}"
    with (OUT / "selection.jsonl").open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    counts = Counter((c["category"], c["source"]) for c in candidates)
    lines = [
        "# Scenario selection report",
        "",
        f"Seed {SEED}. Total scenarios: **{len(candidates)}**.",
        "",
        "| Category | v0.1 | XSTest | AdvBench | Total |",
        "|---|---|---|---|---|",
    ]
    for cat in CATEGORIES:
        row = [counts[(cat, s)] for s in ("veriaudit-v0.1", "xstest", "advbench")]
        lines.append(f"| {cat} | {row[0]} | {row[1]} | {row[2]} | {sum(row)} |")
    lines += ["", "## Selection log", ""] + [f"- {k}: {v}" for k, v in sorted(log.items())]
    (OUT / "selection_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
