"""Translation Agent: language detection and translation that preserves standard identifiers."""

import logging
import re

from app.agents.base import load_prompt
from app.rag.text_extractor import STANDARD_NUMBER_RE
from app.services.llm_service import get_llm
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "kn": "Kannada", "ta": "Tamil"}

_SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),  # Devanagari
    "ta": (0x0B80, 0x0BFF),
    "te": (0x0C00, 0x0C7F),
    "kn": (0x0C80, 0x0CFF),
}

# Identifiers that must survive translation unchanged.
_PROTECTED_RE = re.compile(
    STANDARD_NUMBER_RE.pattern
    + r"|\[\d{1,3}\]|\b(?:Clause|Annex|Table|Amendment)\s+[A-Z0-9][\w.\-]*|\bHUID\b|\bISI\b|https?://\S+",
    re.IGNORECASE,
)


def detect_language(text: str) -> str:
    """Detect English or a supported Indian language from Unicode script usage."""
    counts = {lang: 0 for lang in _SCRIPT_RANGES}
    letters = 0
    for ch in text:
        cp = ord(ch)
        if ch.isalpha():
            letters += 1
        for lang, (lo, hi) in _SCRIPT_RANGES.items():
            if lo <= cp <= hi:
                counts[lang] += 1
    if letters == 0:
        return "en"
    lang, count = max(counts.items(), key=lambda kv: kv[1])
    return lang if count / letters > 0.3 else "en"


def mask_identifiers(text: str) -> tuple[str, list[str]]:
    protected: list[str] = []

    def repl(m: re.Match) -> str:
        protected.append(m.group(0))
        return f"⟦{len(protected) - 1}⟧"

    return _PROTECTED_RE.sub(repl, text), protected


def unmask_identifiers(text: str, protected: list[str]) -> tuple[str, bool]:
    ok = all(f"⟦{i}⟧" in text for i in range(len(protected)))
    for i, original in enumerate(protected):
        text = text.replace(f"⟦{i}⟧", original)
    return text, ok


def translate(text: str, target: str, source: str | None = None) -> tuple[str, bool]:
    """Translate text; returns (text, translated). Falls back to the original text on failure."""
    if not text.strip() or target == (source or detect_language(text)):
        return text, False
    masked, protected = mask_identifiers(text)
    try:
        out = get_llm().chat(
            load_prompt("translation"),
            f"Target language: {LANGUAGE_NAMES.get(target, target)}\n\nText:\n{masked}",
        )
    except AppError as exc:
        logger.warning("Translation failed: %s", exc.message)
        return text, False
    restored, ok = unmask_identifiers(out, protected)
    if not ok:
        logger.warning("Translation dropped protected identifiers; returning original text")
        return text, False
    return restored, True
