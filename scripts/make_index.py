#!/usr/bin/env python3
"""Write index.html linking every build output that exists in the folder."""
import argparse
import html
from pathlib import Path

GROUPS = [
    ("CV", [
        ("cv.pdf", "Standard", "The normal two-page CV."),
        ("cv_public.pdf", "Public", "Public contact details, no phone number."),
        ("cv_print.pdf", "Print", "Greyscale, for printing."),
        ("cv_archive.pdf", "Archive", "PDF/A-2b, for long-term storage."),
    ]),
    ("Accessible versions", [
        ("cv_accessible.pdf", "Accessible", "Larger line spacing, darker text, clear headings."),
        ("cv_dyslexic.pdf", "Dyslexia-friendly", "The accessible layout in the OpenDyslexic font."),
        ("cv_inverted.pdf", "High contrast", "Yellow text on black."),
        ("cv_dyslexic_inverted.pdf", "Dyslexia-friendly, high contrast", "OpenDyslexic, yellow on black."),
    ]),
    ("Cover letter", [
        ("coverletter.pdf", "Cover letter", "The letter on its own."),
        ("cv_with_coverletter.pdf", "Cover letter and CV", "Both in one PDF."),
    ]),
    ("For software and AI tools", [
        ("cv.md", "Markdown", "Generated from the LaTeX source, in reading order."),
        ("cv.json", "JSON", "Sections, roles, highlights and links."),
        ("cv.html", "HTML", "A plain web page that follows dark mode."),
        ("coverletter.md", "Cover letter, Markdown", "The letter as text."),
    ]),
]

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#5d5d58;--card:#fff;--line:#e3e0d8;--link:#1a4d99}
@media (prefers-color-scheme:dark){:root{--bg:#151513;--fg:#ecebe6;--muted:#a9a8a1;--card:#1f1f1c;--line:#34332f;--link:#8fb4ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 system-ui,sans-serif}
main{max-width:52rem;margin:0 auto;padding:2.5rem 1rem 4rem}h1{margin:0 0 .25rem;font-size:2rem}
.meta{color:var(--muted);margin:0 0 2rem}h2{font-size:1.1rem;margin:2rem 0 .75rem}
ul{list-style:none;padding:0;margin:0;display:grid;gap:.6rem}
li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem}
a{color:var(--link);font-weight:600}span{display:block;color:var(--muted);font-size:.95rem}
img{width:100%;max-width:22rem;border:1px solid var(--line);border-radius:6px;background:#fff}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--version", default="local")
    ap.add_argument("--date", default="")
    args = ap.parse_args()
    out = Path(args.dir)

    parts = []
    if (out / "cv_preview.png").exists():
        parts.append('<a href="cv.pdf"><img src="cv_preview.png" alt="Preview of the first page of the CV"></a>')
    for title, items in GROUPS:
        rows = [
            f'<li><a href="{f}">{html.escape(label)}</a><span>{html.escape(desc)}</span></li>'
            for f, label, desc in items
            if (out / f).exists()
        ]
        if rows:
            parts.append(f"<h2>{html.escape(title)}</h2><ul>{''.join(rows)}</ul>")

    meta = " · ".join(x for x in (args.date, args.version) if x)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CV builds</title><style>{CSS}</style></head>
<body><main>
<h1>CV builds</h1>
<p class="meta">{html.escape(meta)} · built by <a href="https://github.com/benkelly/cv-pipeline">cv-pipeline</a></p>
{''.join(parts)}
</main></body></html>
"""
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote {out / 'index.html'}")


if __name__ == "__main__":
    main()
