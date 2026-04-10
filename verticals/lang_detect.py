"""Lightweight language detection — Hindi vs English.

Uses Unicode codepoint heuristics (Devanagari range U+0900–U+097F)
to classify input text. No external dependencies required.
"""


def detect_language(text: str) -> str:
    """Return 'hi' if majority of alpha characters are Devanagari, else 'en'.

    Args:
        text: Input text to classify.

    Returns:
        'hi' for Hindi, 'en' for English (or any Latin-script text).
    """
    if not text or not text.strip():
        return "en"

    devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    latin_count = sum(1 for c in text if c.isascii() and c.isalpha())

    return "hi" if devanagari_count > latin_count else "en"
