"""Automated linguistic quality checks for VeriAudit-X variants.

These are screens, not proofs. A failed check flags a record for review; a
passed check never verifies equivalence (only human ratings do).

English-word detection uses `wordfreq` English Zipf frequencies with a Roman
Urdu stop-list overriding it (Roman Urdu function words such as "main",
"to", "hai" are also English or English-frequent strings).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.v2.judges.rule_judge import script_counts

# Common Roman Urdu function words, pronouns, auxiliaries and light verbs (lower-case,
# several spellings each). Used to recognise the Urdu matrix language in Latin script.
ROMAN_URDU_LEXICON = frozenset(
    """
    aap ap apna apni apne aur or bhi bhe ka ki ke ko kay se say sey mein main mai me mujhe mujh mjhe hum hm ham humein tum tu tumhe
    yeh ye yah woh wo vo voh is us un in inhe unhe iss uss jo jis jin kya kia kyun kyon kyunke kaise kese kaisay kahan kab kitna kitni
    kitne kaun kon hai hain hay he hy ho hoon hun hu hota hoti hote hua hui huay hue tha thi the thay raha rahi rahe rha rhi
    nahi nahin nai nhi na mat sakta sakti sakte skta skti skte sakoon sakon karo karein karen kijiye kijie karna karni karne kar kr
    karta karti karte kiya kia kiye ki diya diye dein dena deni dijiye do de chahiye chahye chahta chahti chahte lena leni lo le
    liye lie liya wala wali wale waala walay jaye jaaye jaye jata jati jate gaya gayi gaye gya gyi bana banao banayein banaen likh
    likho likhein likhen likhiye batao bataen batayein bataiye samjhao samjha samajh pata chale chalay ab abhi phir agar toh to tou
    lekin magar ya yaa aik ek koi kuch sab bohat bahut zyada kam saath sath pehle baad andar upar neeche taraf jagah waqt din raat
    apni khud zara bas haan han ji jee shukriya meherbani please plz kaisay unka unki unke iska iski iske uska uski uske mera meri
    mere tera teri tere hamara hamari hamare tumhara tumhari tumhare
    """.split()
)

_LATIN_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def tokens(text: str) -> list[str]:
    return _LATIN_WORD.findall(text.lower())


def is_english_word(word: str) -> bool:
    from wordfreq import zipf_frequency

    if word in ROMAN_URDU_LEXICON:
        return False
    z = zipf_frequency(word, "en")
    return z >= 3.0 or (len(word) >= 6 and z >= 1.5)


def _common_english(word: str) -> bool:
    from wordfreq import zipf_frequency

    return zipf_frequency(word, "en") >= 3.0


def english_token_ratio(text: str) -> float:
    toks = tokens(text)
    return sum(is_english_word(t) for t in toks) / len(toks) if toks else 0.0


def roman_urdu_marker_ratio(text: str) -> float:
    toks = tokens(text)
    return sum(t in ROMAN_URDU_LEXICON for t in toks) / len(toks) if toks else 0.0


def script_ratios(text: str) -> dict[str, float]:
    c = script_counts(text)
    total = sum(c.values()) or 1
    return {k: v / total for k, v in c.items()}


# Roman Urdu spelling canonicalisation (only for comparing spelling variants)
_RU_CANON = [
    (r"\bnahin\b|\bnai\b|\bnhi\b|\bnahi\b", "nahi"),
    (r"\bkia\b|\bkya\b", "kya"),
    (r"\bhy\b|\bhay\b|\bhe\b|\bhai\b", "hai"),
    (r"\bmai\b|\bme\b|\bmein\b", "mein"),
    (r"\bkay\b|\bke\b", "ke"),
    (r"\bsay\b|\bsey\b|\bse\b", "se"),
    (r"\bek\b|\baik\b", "aik"),
    (r"\bkr\b|\bkar\b", "kar"),
    (r"aa", "a"),
    (r"ee", "i"),
    (r"oo", "u"),
    (r"(.)\1", r"\1"),
]


def canonical_roman_urdu(text: str) -> str:
    t = " ".join(tokens(text))
    for pat, rep in _RU_CANON:
        t = re.sub(pat, rep, t)
    return t


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    value: float | str | None = None
    detail: str | None = None


def check_variant(language: str, text: str, english_source: str, condition: str = "base", base_text: str | None = None) -> list[Check]:
    """Checks for one variant. `base_text` is the base variant a controlled transformation derives from."""
    out: list[Check] = []
    sr = script_ratios(text)
    arabic, latin = sr["arabic"], sr["latin"]
    ru = roman_urdu_marker_ratio(text)
    en = english_token_ratio(text)

    if language == "english":
        out.append(Check("script_consistency", latin >= 0.95, round(latin, 3), "latin ratio"))
        # English homographs in the lexicon (is, in, the, to, do, me, main...) are not evidence of
        # Roman Urdu in an English text; count only lexicon words that are not common English words.
        toks = tokens(text)
        ru_en = sum(t in ROMAN_URDU_LEXICON and not _common_english(t) for t in toks) / len(toks) if toks else 0.0
        out.append(Check("no_roman_urdu_in_english", ru_en < 0.08, round(ru_en, 3), "Roman Urdu words that are not English homographs"))
    elif language == "urdu":
        if condition == "T6":
            out.append(Check("script_mixing_present", arabic >= 0.4 and latin >= 0.05, f"ar={arabic:.2f},la={latin:.2f}"))
        else:
            out.append(Check("script_consistency", arabic >= 0.9, round(arabic, 3), "perso-arabic ratio"))
    elif language == "roman_urdu":
        out.append(Check("script_consistency", latin >= 0.95, round(latin, 3), "latin ratio"))
        out.append(Check("roman_urdu_markers", ru >= 0.15, round(ru, 3), "share of Roman Urdu function words"))
        out.append(Check("not_mostly_english", en <= 0.5, round(en, 3), "English token ratio"))
    elif language == "code_switched":
        out.append(Check("script_consistency", latin >= 0.95 or (arabic > 0 and latin > 0), f"ar={arabic:.2f},la={latin:.2f}"))
        out.append(Check("urdu_matrix_present", ru >= 0.1, round(ru, 3)))
        lo, hi = {"T4": (0.0, 0.35), "T5": (0.45, 1.0)}.get(condition, (0.1, 0.9))
        out.append(Check("english_ratio_in_range", lo <= en <= hi, round(en, 3), f"target [{lo}, {hi}]"))

    if language != "english":
        n_src, n = len(english_source.split()), len(text.split())
        ratio = n / n_src if n_src else 0.0
        out.append(Check("length_ratio", 0.5 <= ratio <= 2.5, round(ratio, 2), "words vs English source"))
        out.append(Check("differs_from_english", text.strip().lower() != english_source.strip().lower()))

    if condition in ("T1", "T2") and base_text is not None:
        same_raw = text.strip().lower() == base_text.strip().lower()
        sim = _jaccard(canonical_roman_urdu(text), canonical_roman_urdu(base_text))
        out.append(Check("spelling_variant_only", (not same_raw) and sim >= 0.6, round(sim, 3), "canonicalised token Jaccard vs base"))
    if condition in ("T3", "T4", "T5", "T6") and base_text is not None:
        out.append(Check("differs_from_base", text.strip() != base_text.strip()))
    return out


def near_duplicates(texts: dict[str, str], threshold: float = 0.8) -> list[tuple[str, str, float]]:
    """Pairs of ids whose char 3-5-gram TF-IDF cosine similarity >= threshold."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    ids = list(texts)
    if len(ids) < 2:
        return []
    m = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True).fit_transform([texts[i] for i in ids])
    sim = cosine_similarity(m)
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if sim[i, j] >= threshold:
                pairs.append((ids[i], ids[j], float(sim[i, j])))
    return pairs


_STOP = frozenset(
    "a an the to of and or for in on at by with from into that this these those how what which who can could would should "
    "is are be been being it its as your you their them they someone people person users user others other some any "
    "write create develop provide give make teach explain outline instruct generate design produce show describe guide "
    "tutorial plan program script app tool step steps detailed instructions way ways best using use used get getting".split()
)


def content_words(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return frozenset(w[:-1] if w.endswith("s") and len(w) > 4 else w for w in words if w not in _STOP and len(w) > 2)


def content_word_duplicates(texts: dict[str, str], threshold: float = 0.5) -> list[tuple[str, str, float]]:
    """Pairs whose content-word Jaccard >= threshold (catches template paraphrases TF-IDF misses)."""
    ids = list(texts)
    sets = {i: content_words(texts[i]) for i in ids}
    out = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            sa, sb = sets[ids[a]], sets[ids[b]]
            if sa and sb:
                j = len(sa & sb) / len(sa | sb)
                if j >= threshold:
                    out.append((ids[a], ids[b], j))
    return out
