# Scenario selection report

Seed 20261112. Total scenarios: **200**.

| Category | v0.1 | XSTest | AdvBench | Total |
|---|---|---|---|---|
| cybercrime | 5 | 0 | 24 | 29 |
| weapons | 5 | 3 | 6 | 14 |
| self_harm | 5 | 5 | 11 | 21 |
| hate_speech | 5 | 12 | 11 | 28 |
| misinformation | 5 | 3 | 20 | 28 |
| fraud | 5 | 3 | 21 | 29 |
| privacy_violation | 0 | 9 | 14 | 23 |
| violence | 0 | 25 | 3 | 28 |

## Selection log

- advbench categorised: 408
- advbench excluded:cbrn_or_explosives: 43
- advbench excluded:out_of_taxonomy_drugs: 19
- advbench excluded:out_of_taxonomy_property_or_other: 22
- advbench excluded:override:cbrn_or_explosives: 1
- advbench excluded:override:not_harmful: 2
- advbench excluded:sexual_or_minors: 18
- advbench near-duplicates dropped: 176
- advbench unassigned: 7
- shortfall privacy_violation: 2
- shortfall self_harm: 4
- shortfall weapons: 11
- top-up cybercrime: 4
- top-up fraud: 4
- top-up hate_speech: 3
- top-up misinformation: 3
- top-up violence: 3
- v0.1 included: 30
- xstest excluded:cbrn_or_explosives: 9
- xstest excluded:out_of_taxonomy_drugs: 7
- xstest excluded:out_of_taxonomy_property_or_other: 16
- xstest excluded:override:out_of_taxonomy_drugs: 2
- xstest excluded:sexual_or_minors: 8
- xstest pair focus mismatch (skipped): 1
- xstest selected: 60
- xstest unassigned: 6
