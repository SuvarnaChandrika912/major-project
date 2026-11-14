"""Defences against prompt injection from untrusted content (uploaded PDFs, retrieved chunks)."""

import re

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above)\s+(instructions|prompts?|rules)",
    r"disregard\s+(all\s+)?(the\s+)?(previous|prior|above|system)\s+\w+",
    r"forget\s+(all\s+)?(your|the)\s+(instructions|rules)",
    r"you\s+are\s+now\s+(a|an|the)\s+",
    r"new\s+instructions?\s*:",
    r"system\s*prompt",
    r"</?\s*(system|assistant|user|instructions?)\s*>",
    r"\[\s*(system|inst)\s*\]",
    r"act\s+as\s+(if\s+you\s+are\s+)?(a|an)\s+",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_untrusted(text: str, max_chars: int | None = None) -> str:
    """Neutralise instruction-like phrases so they are read as quoted data, not commands."""
    cleaned = _INJECTION_RE.sub(lambda m: f"[removed instruction-like text: {m.group(0)[:30]!r}]", text)
    cleaned = cleaned.replace("<document", "&lt;document").replace("</document", "&lt;/document")
    if max_chars and len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + " …"
    return cleaned


def contains_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))
