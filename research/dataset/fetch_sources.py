"""Download licensed source datasets into data/sources/ and record SHA-256 + licence.

Run: python research/dataset/fetch_sources.py
Re-running verifies the pinned hashes in data/sources/SOURCES.json.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "data" / "sources"

SOURCES = [
    {
        "name": "advbench_harmful_behaviors.csv",
        "url": "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv",
        "licence": "MIT",
        "licence_url": "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/LICENSE",
        "citation": "Zou, Wang, Kolter, Fredrikson (2023). Universal and Transferable Adversarial Attacks on Aligned Language Models. arXiv:2307.15043",
        "used_fields": ["goal"],
    },
    {
        "name": "xstest_prompts.csv",
        "url": "https://raw.githubusercontent.com/paul-rottger/exaggerated-safety/main/xstest_prompts.csv",
        "licence": "CC-BY-4.0 (prompts only; model completions in the source repo are under other licences and are not used)",
        "licence_url": "https://github.com/paul-rottger/xstest",
        "citation": "Röttger et al. (2024). XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models. NAACL 2024",
        "used_fields": ["id", "prompt", "type", "label", "focus"],
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest_path = DEST / "SOURCES.json"
    pinned = {s["name"]: s.get("sha256") for s in json.loads(manifest_path.read_text())} if manifest_path.exists() else {}
    out = []
    for src in SOURCES:
        path = DEST / src["name"]
        if not path.exists():
            with urllib.request.urlopen(src["url"], timeout=60) as r:  # noqa: S310 (fixed https URLs)
                path.write_bytes(r.read())
        digest = sha256(path)
        if pinned.get(src["name"]) and pinned[src["name"]] != digest:
            raise SystemExit(f"hash mismatch for {src['name']}: pinned {pinned[src['name']]}, got {digest}")
        out.append({**src, "sha256": digest})
    manifest_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps([{k: s[k] for k in ("name", "sha256")} for s in out], indent=2))


if __name__ == "__main__":
    main()
