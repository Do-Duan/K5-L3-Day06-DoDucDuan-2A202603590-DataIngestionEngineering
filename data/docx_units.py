"""Shared DOCX paragraph and heading metadata helpers for benchmark validation."""
import re
from pathlib import Path
from docx import Document


def load_paragraphs(path):
    """Return non-empty paragraphs indexed by their 1-based source paragraph position."""
    doc = Document(Path(path))
    result = []
    chapter = None
    section = None
    idx = 0
    for paragraph in doc.paragraphs:
        text = " ".join(paragraph.text.split())
        if not text:
            continue
        idx += 1
        appendix = re.match(r"^appendix\s+([a-z])\b", text, re.I)
        if appendix:
            chapter, section = "appendices", f"Appendix {appendix.group(1).upper()}"
        elif re.match(r"^chapter\s+\d+", text, re.I):
            chapter = int(re.search(r"\d+", text).group())
            section = str(chapter)
        elif re.match(r"^\d+(?:\.\d+)+\b", text):
            section = re.match(r"^\d+(?:\.\d+)+", text).group()
        elif re.fullmatch(r"(?:0\.0|[135]\.0)", text):
            # Rubric table rows inherit the nearest Appendix heading; their leading
            # score is not a section heading.
            pass
        result.append({"idx": idx, "text": text, "chapter": chapter, "section": section})
    return result


def matches(paragraph, filters):
    """Match all supplied filter keys against extracted paragraph metadata."""
    return all(paragraph.get(key) == value for key, value in filters.items())
