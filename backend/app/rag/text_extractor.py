"""Text cleanup and BIS-specific identifier extraction helpers."""

import re
import unicodedata

# IS 1293 : 2019, IS 302 (Part 1), IS/IEC 60335-1, IS 14543:2016 etc.
STANDARD_NUMBER_RE = re.compile(
    r"\bIS(?:\s*/\s*(?:IEC|ISO)(?:\s*/\s*IEC)?)?\s*[:\-]?\s*"
    r"(\d{1,6}(?:\s*-\s*\d+)*)"
    r"(\s*\(\s*Part\s*\d+(?:\s*/\s*Sec(?:tion)?\s*\d+)?\s*\))?"
    r"(\s*:\s*\d{4})?",
    re.IGNORECASE,
)

# Clause headings such as "4", "4.2", "4.2.1 Requirements", "ANNEX A", "A-2.1"
CLAUSE_HEADING_RE = re.compile(
    r"^\s*(?P<num>(?:\d{1,2}(?:\.\d{1,3}){0,4})|(?:[A-H]-\d{1,2}(?:\.\d{1,3}){0,3}))"
    r"(?:\s+|\s*[.)]\s+)(?P<title>[A-Z][^\n]{0,150})?$"
)
ANNEX_RE = re.compile(r"^\s*ANNEX(?:URE)?\s+(?P<num>[A-Z])\b(?P<title>.*)$", re.IGNORECASE)

AMENDMENT_RE = re.compile(r"\bAmendment\s+No\.?\s*(\d+)", re.IGNORECASE)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "")  # soft hyphen
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def canonical_standard_number(raw: str) -> str:
    """Normalise an IS identifier, e.g. 'is 1293:2019' -> 'IS 1293:2019'."""
    match = STANDARD_NUMBER_RE.search(raw)
    if not match:
        return raw.strip().upper()
    full = match.group(0)
    full = re.sub(r"\s+", " ", full).strip()
    full = re.sub(r"^is", "IS", full, flags=re.IGNORECASE)
    full = re.sub(r"\s*:\s*", ":", full)
    full = re.sub(r"\s*\(\s*part\s*", " (Part ", full, flags=re.IGNORECASE)
    full = re.sub(r"\s*\)", ")", full)
    full = re.sub(r"IS\s*-\s*", "IS ", full)
    if re.match(r"IS\d", full):
        full = "IS " + full[2:]
    return full


def find_standard_numbers(text: str) -> list[str]:
    seen: list[str] = []
    for match in STANDARD_NUMBER_RE.finditer(text):
        num = canonical_standard_number(match.group(0))
        if num not in seen:
            seen.append(num)
    return seen


def detect_clause_heading(line: str) -> tuple[str, str] | None:
    """Return (clause_number, title) if the line looks like a clause or annex heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 160:
        return None
    annex = ANNEX_RE.match(stripped)
    if annex:
        return f"Annex {annex.group('num').upper()}", (annex.group("title") or "").strip(" -:")
    match = CLAUSE_HEADING_RE.match(stripped)
    if not match:
        return None
    num = match.group("num")
    title = (match.group("title") or "").strip()
    # Reject bare numbers that are probably page numbers or table values.
    if not title and "." not in num and "-" not in num:
        return None
    # Reject numeric-looking lines like "4.5 mm" or "2.0 kg".
    if title and re.match(r"^(mm|cm|m|kg|g|V|W|A|Hz|°C|%)\b", title):
        return None
    return num, title


def find_amendment(text: str) -> str | None:
    match = AMENDMENT_RE.search(text)
    return match.group(1) if match else None
