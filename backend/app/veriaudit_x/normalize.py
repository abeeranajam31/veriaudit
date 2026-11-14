"""Text normalisation used only for duplicate / leakage detection.

Deliberately conservative: it removes differences that do not change what a
string says (Unicode form, case, punctuation, whitespace, Urdu diacritics,
Arabic-vs-Urdu codepoints for the same letter), so that two records whose
texts differ only in those respects are treated as the same text. It does
NOT attempt Roman Urdu spelling normalisation ("kya"/"kia"): spelling
variants are a controlled transformation in VeriAudit-X, and they stay tied
together through intent_id/scenario_id rather than through text matching.
"""

from __future__ import annotations

import re
import unicodedata

# Arabic harakat + superscript alef + Urdu-specific marks that are optional in practice
_DIACRITICS = re.compile("[ً-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
# Arabic-block codepoints that render like the Urdu letters used in normal text
_CODEPOINT_MAP = str.maketrans(
    {
        "ي": "ی",  # Arabic yeh  -> Farsi/Urdu yeh
        "ى": "ی",  # alef maksura -> Urdu yeh
        "ك": "ک",  # Arabic kaf  -> keheh
        "ه": "ہ",  # Arabic heh  -> heh goal
    }
)
_PUNCT_OR_SYMBOL = re.compile(r"[\W_]+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(_TATWEEL, "")
    text = _DIACRITICS.sub("", text)
    text = text.translate(_CODEPOINT_MAP)
    text = text.casefold()
    text = _PUNCT_OR_SYMBOL.sub(" ", text)
    return " ".join(text.split())
