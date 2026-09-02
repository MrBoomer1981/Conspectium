"""Plain-text extraction from a .docx upload.

No model call: a Word file is already machine text, so its structure maps
straight to markdown — heading styles become `#` prefixes, every other
paragraph is copied as is. Images and tables are ignored on purpose
(PLAN.md task 9: text and headings only).
"""

from __future__ import annotations

import io

import docx


def extract_markdown(data: bytes) -> str:
    """Turn a .docx byte string into markdown. Word's built-in heading styles
    ("Title", "Heading 1" … "Heading 9") become `#` prefixes with the depth
    capped at 6; blank paragraphs are dropped; everything else is copied."""
    document = docx.Document(io.BytesIO(data))
    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        level = _heading_level(paragraph)
        lines.append(f"{'#' * level} {text}" if level else text)
    return "\n\n".join(lines)


def _heading_level(paragraph) -> int:
    """Markdown heading depth for a paragraph, or 0 when it is body text."""
    name = (paragraph.style.name if paragraph.style else "") or ""
    if name == "Title":
        return 1
    if name.startswith("Heading "):
        tail = name[len("Heading ") :].strip()
        if tail.isdigit():
            return min(int(tail), 6)
    return 0


def derive_title(markdown: str, fallback: str) -> str:
    """First non-empty line, stripped of heading marks and capped at 60
    characters. `fallback` (usually the file name) is used when there is no
    usable line."""
    for line in markdown.splitlines():
        stripped = line.lstrip("#").strip()
        if stripped:
            return stripped[:60]
    return fallback[:60] if fallback else "Untitled"
