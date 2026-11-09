import re
import unicodedata


def normalize_name(s: str) -> str:
    """Lowercase, strip accents/punctuation, drop a leading 'the ', collapse whitespace."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    return s
