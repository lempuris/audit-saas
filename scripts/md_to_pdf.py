"""Render Markdown docs to PDF (pure Python, no system libraries or fonts).

Usage:
    uv run --with markdown --with xhtml2pdf python scripts/md_to_pdf.py <file.md> [<file.md> ...]

Each input writes a sibling <file>.pdf. A few symbol glyphs that the built-in
PDF font can't encode (arrows, check marks, math comparators) are mapped to
ASCII so the output is reliable across machines; WinAnsi punctuation
(em/en-dashes, curly quotes, bullets, ellipses) is preserved as-is.
"""

import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa

# Glyphs outside WinAnsi that the default PDF font would drop → ASCII fallback.
_GLYPHS = {
    "→": "->",  # →
    "⇒": "=>",  # ⇒
    "↔": "<->",  # ↔
    "✓": "[check]",  # ✓
    "✔": "[check]",  # ✔
    "✅": "[done]",  # ✅
    "✗": "[x]",  # ✗
    "≥": ">=",  # ≥
    "≤": "<=",  # ≤
    "×": "x",  # ×
    # Smart punctuation → ASCII so there's no encoding ambiguity in the output.
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",  # left single quote
    "’": "'",  # right single quote
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "…": "...",  # ellipsis
    "•": "-",  # bullet
}

_CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: Helvetica; font-size: 10.5pt; color: #1f2937; line-height: 1.45; }
h1 { font-size: 20pt; color: #0f172a; }
h2 { font-size: 15pt; color: #0f172a; margin-top: 18pt; border-bottom: 0.5pt solid #e2e8f0;
     padding-bottom: 3pt; }
h3 { font-size: 12pt; color: #0f172a; margin-top: 12pt; }
p, li { margin: 3pt 0; }
code { font-family: Courier; background-color: #f1f5f9; font-size: 9.5pt; }
pre { background-color: #f1f5f9; padding: 6pt; }
blockquote { border-left: 3pt solid #cbd5e1; padding-left: 8pt; color: #475569; margin-left: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 0.5pt solid #cbd5e1; padding: 4pt; text-align: left; }
th { background-color: #f8fafc; }
a { color: #2563eb; text-decoration: none; }
"""


def _normalize(text: str) -> str:
    for glyph, ascii_form in _GLYPHS.items():
        text = text.replace(glyph, ascii_form)
    return text


def convert(md_path: Path) -> Path:
    text = _normalize(md_path.read_text(encoding="utf-8"))
    body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    html = f"<html><head><style>{_CSS}</style></head><body>{body}</body></html>"
    pdf_path = md_path.with_suffix(".pdf")
    with pdf_path.open("wb") as out:
        result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        raise SystemExit(f"Failed to render {md_path}")
    return pdf_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Provide one or more Markdown file paths")
    for arg in sys.argv[1:]:
        out = convert(Path(arg))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
