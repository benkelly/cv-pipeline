#!/usr/bin/env python3
"""Generate Markdown, JSON and HTML versions of the CV straight from the LaTeX source.

This replaces running docling over the finished PDF. The PDF is two-column, so
PDF extraction scrambled the section order, rendered the name as an embedded
image (the JSON was over 1 MB) and invented headings from wrapped lines.
Reading cv.tex directly gives the real structure.

Usage:
    python3 scripts/tex_to_formats.py --source cv.tex --out-base cv [--public] [--version V]

Writes <out-base>.md, <out-base>.json and <out-base>.html. With --public the
contact block uses the work email and omits the phone number, matching
cv_public.pdf. For coverletter.tex, nothing is written unless the
\\coverletter{...}{...} block is uncommented.

Only the standard library is used, so it runs in the build container as-is.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------- #
# LaTeX parsing helpers
# --------------------------------------------------------------------------- #


def strip_comments(tex: str) -> str:
    """Remove % comments, keeping escaped \\%."""
    out = []
    for line in tex.splitlines():
        i = 0
        while True:
            j = line.find("%", i)
            if j == -1:
                out.append(line)
                break
            if j > 0 and line[j - 1] == "\\":
                i = j + 1
                continue
            out.append(line[:j])
            break
    return "\n".join(out)


def read_group(s: str, i: int, open_ch: str = "{", close_ch: str = "}") -> tuple[str, int]:
    """Read a balanced group starting at s[i] == open_ch. Returns (content, index after group)."""
    if i >= len(s) or s[i] != open_ch:
        raise ValueError(f"expected {open_ch!r} at {i}: {s[i:i + 30]!r}")
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced group")


def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def find_command(s: str, name: str, start: int = 0) -> int:
    """Index of \\name not followed by a letter (so \\item doesn't match \\itemize)."""
    pat = re.compile(r"\\" + re.escape(name) + r"(?![A-Za-z])")
    m = pat.search(s, start)
    return m.start() if m else -1


# --------------------------------------------------------------------------- #
# Inline rendering: LaTeX -> plain text / Markdown / HTML
# --------------------------------------------------------------------------- #

ESCAPES = {"&": "&", "#": "#", "%": "%", "_": "_", "$": "$", "{": "{", "}": "}", "@": "", ",": " ", " ": " "}
# Commands whose single argument is dropped entirely
DROP_WITH_ARG = {"color", "hypersetup", "definecolor", "colorlet", "vspace", "hspace", "label", "setlength"}
# Size / switch commands with no argument
DROP_SWITCH = {"small", "large", "Large", "LARGE", "normalsize", "footnotesize", "tiny",
               "raggedright", "raggedleft", "centering", "noindent", "par", "today"}


@dataclass
class Link:
    text: str
    url: str


def render_inline(tex: str, fmt: str, links: list[Link] | None = None) -> str:
    """Render inline LaTeX. fmt is 'text', 'md' or 'html'."""
    out: list[str] = []
    i = 0
    n = len(tex)

    def esc(t: str) -> str:
        return html.escape(t, quote=False) if fmt == "html" else t

    while i < n:
        c = tex[i]
        if c == "\\":
            # Line break
            if tex.startswith("\\\\", i):
                out.append("\n")
                i += 2
                continue
            # Escaped character
            if i + 1 < n and not tex[i + 1].isalpha():
                out.append(esc(ESCAPES.get(tex[i + 1], tex[i + 1])))
                i += 2
                continue
            m = re.match(r"\\([A-Za-z]+)\*?", tex[i:])
            name = m.group(1)
            i += m.end()
            if name in ("textbf", "textit", "emph", "texttt"):
                j = skip_ws(tex, i)
                inner, i = read_group(tex, j)
                r = render_inline(inner, fmt, links)
                if fmt == "md":
                    mark = "**" if name == "textbf" else ("`" if name == "texttt" else "*")
                    # Keep markers tight around the text
                    lead = r[: len(r) - len(r.lstrip())]
                    trail = r[len(r.rstrip()):]
                    core = r.strip()
                    out.append(f"{lead}{mark}{core}{mark}{trail}" if core else r)
                elif fmt == "html":
                    tag = {"textbf": "strong", "texttt": "code"}.get(name, "em")
                    out.append(f"<{tag}>{r}</{tag}>")
                else:
                    out.append(r)
            elif name == "href":
                url, i = read_group(tex, skip_ws(tex, i))
                text_tex, i = read_group(tex, skip_ws(tex, i))
                text_plain = render_inline(text_tex, "text").strip()
                text = render_inline(text_tex, fmt, links)
                url = url.replace("\\#", "#").replace("\\%", "%").replace("\\_", "_")
                if links is not None:
                    links.append(Link(text_plain, url))
                if fmt == "md":
                    out.append(f"[{text}]({url})")
                elif fmt == "html":
                    out.append(f'<a href="{html.escape(url)}">{text}</a>')
                else:
                    out.append(text)
            elif name == "url":
                url, i = read_group(tex, skip_ws(tex, i))
                if links is not None:
                    links.append(Link(url, url))
                out.append(f"<{url}>" if fmt == "md" else
                           (f'<a href="{html.escape(url)}">{html.escape(url)}</a>' if fmt == "html" else url))
            elif name == "newline":
                out.append(" ")
            elif name in DROP_WITH_ARG:
                j = skip_ws(tex, i)
                if j < n and tex[j] == "{":
                    _, i = read_group(tex, j)
            elif name in DROP_SWITCH:
                pass
            else:
                # Unknown command: drop the name, keep any argument's content
                j = skip_ws(tex, i)
                if j < n and tex[j] == "{":
                    inner, i = read_group(tex, j)
                    out.append(render_inline(inner, fmt, links))
            continue
        if c in "{}":
            i += 1
            continue
        if c == "~":
            out.append(" ")
            i += 1
            continue
        if tex.startswith("``", i):
            out.append("\u201c")
            i += 2
            continue
        if tex.startswith("''", i):
            out.append("\u201d")
            i += 2
            continue
        if tex.startswith("---", i):
            out.append("\u2014")
            i += 3
            continue
        if tex.startswith("--", i):
            out.append("\u2013")
            i += 2
            continue
        out.append(esc(c))
        i += 1

    text = "".join(out)
    # Collapse whitespace within lines, keep explicit breaks
    lines = [re.sub(r"[ \t\r\n]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Document model
# --------------------------------------------------------------------------- #


@dataclass
class Entry:
    title: str               # e.g. job title; may be empty
    details: list[str]       # LaTeX lines before any list
    bullets: list[str]       # LaTeX \item contents
    note: str = ""           # optional first argument
    prose: bool = False      # render lines as paragraphs, never as a list


@dataclass
class Section:
    title: str
    entries: list[Entry] = field(default_factory=list)


def split_body(body: str) -> tuple[list[str], list[str]]:
    """Split a section body into detail lines and itemize bullets."""
    details: list[str] = []
    bullets: list[str] = []
    rest = body
    while True:
        b = rest.find("\\begin{itemize}")
        if b == -1:
            details += [ln for ln in re.split(r"\\\\", rest) if ln.strip()]
            break
        details += [ln for ln in re.split(r"\\\\", rest[:b]) if ln.strip()]
        e = rest.find("\\end{itemize}", b)
        inner = rest[b + len("\\begin{itemize}"):e]
        parts = re.split(r"\\item(?![A-Za-z])", inner)
        bullets += [p.strip() for p in parts[1:] if p.strip()]
        rest = rest[e + len("\\end{itemize}"):]
    return [d.strip() for d in details], bullets


def parse_cv(tex: str) -> list[Section]:
    tex = strip_comments(tex)
    sections: list[Section] = []
    pos = 0
    while True:
        k = find_command(tex, "cvsection", pos)
        if k == -1:
            break
        i = skip_ws(tex, k + len("\\cvsection"))
        note = ""
        if i < len(tex) and tex[i] == "[":
            note, i = read_group(tex, i, "[", "]")
        title, i = read_group(tex, skip_ws(tex, i))
        heading, i = read_group(tex, skip_ws(tex, i))
        body, i = read_group(tex, skip_ws(tex, i))
        pos = i
        details, bullets = split_body(body)
        entry = Entry(title=heading.strip(), details=details, bullets=bullets, note=note.strip())
        title_plain = render_inline(title, "text").strip()
        if title_plain or not sections:
            sections.append(Section(title=title_plain or "Other"))
        sections[-1].entries.append(entry)
    return sections


def parse_layout(layout: str, public: bool) -> tuple[str, str, list[Link]]:
    """Return (name, location, contact links) from layout.tex."""
    layout = strip_comments(layout)
    m = re.search(r"\\textbf\{([^{}]*?)\\newline\s*([^{}]*?)\}", layout)
    name = f"{m.group(1).strip()} {m.group(2).strip()}" if m else "Your Name"

    k = layout.find("\\newcommand{\\contactinfo}")
    block, _ = read_group(layout, layout.find("{", k + len("\\newcommand{\\contactinfo}")))
    # Resolve \ifthenelse{\boolean{showworkinfo}}{WORK}{PERSONAL}
    t = find_command(block, "ifthenelse")
    if t != -1:
        j = skip_ws(block, t + len("\\ifthenelse"))
        _, j = read_group(block, j)
        work, j = read_group(block, skip_ws(block, j))
        personal, j = read_group(block, skip_ws(block, j))
        block = block[:t] + (work if public else personal) + block[j:]

    links: list[Link] = []
    location = ""
    for line in re.split(r"\\\\", block):
        if "\\href" in line:
            render_inline(line, "text", links)
        else:
            plain = render_inline(line, "text").strip()
            if plain and not location:
                location = plain
    return name, location, links


def parse_coverletter(tex: str) -> tuple[str, str] | None:
    """Return (recipient, body) LaTeX if a \\coverletter block is active."""
    tex = strip_comments(tex)
    k = find_command(tex, "coverletter")
    if k == -1:
        return None
    recipient_def = ""
    d = tex.find("\\def\\recipient")
    if d != -1:
        recipient_def, _ = read_group(tex, tex.find("{", d))
    i = skip_ws(tex, k + len("\\coverletter"))
    recipient, i = read_group(tex, i)
    body, _ = read_group(tex, skip_ws(tex, i))
    if recipient.strip() == "\\recipient":
        recipient = recipient_def
    return recipient, body


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #


def lines_of(tex_lines: list[str], fmt: str, links: list[Link] | None = None) -> list[str]:
    out = []
    for ln in tex_lines:
        r = render_inline(ln, fmt, links)
        out += [x for x in r.split("\n") if x.strip()]
    return out


def entry_as_list(entry: Entry) -> bool:
    """Untitled entries with several lines (Skills, Projects) read best as a list."""
    return not entry.prose and not entry.title and not entry.bullets and len(entry.details) > 1


def to_markdown(name: str, location: str, contacts: list[Link], sections: list[Section]) -> str:
    md = [f"# {name}", ""]
    contact_bits = ([location] if location else []) + [f"[{c.text}]({c.url})" for c in contacts]
    if contact_bits:
        md += [" · ".join(contact_bits), ""]
    for sec in sections:
        md += [f"## {sec.title}", ""]
        for e in sec.entries:
            if e.title:
                md += [f"### {render_inline(e.title, 'md')}", ""]
            det = lines_of(e.details, "md")
            if e.prose:
                md += ["\n\n".join(det), ""]
            elif entry_as_list(e):
                md += [f"- {d}" for d in det] + [""]
            elif det:
                md += ["  \n".join(det), ""]
            if e.bullets:
                md += [f"- {render_inline(b, 'md').replace(chr(10), ' ')}" for b in e.bullets] + [""]
            if e.note:
                md += [f"*{render_inline(e.note, 'md')}*", ""]
    return "\n".join(md).rstrip() + "\n"


def to_json(name: str, location: str, contacts: list[Link], sections: list[Section],
            source: str, version: str, public: bool) -> dict:
    def links_dict(ls: list[Link]) -> list[dict]:
        return [{"text": l.text, "url": l.url} for l in ls]

    out_sections = []
    for sec in sections:
        entries = []
        for e in sec.entries:
            links: list[Link] = []
            item = {}
            if e.title:
                item["title"] = render_inline(e.title, "text", links)
            item["details"] = lines_of(e.details, "text", links)
            if e.bullets:
                item["highlights"] = [render_inline(b, "text", links).replace("\n", " ") for b in e.bullets]
            if e.note:
                item["note"] = render_inline(e.note, "text", links)
            if links:
                item["links"] = links_dict(links)
            entries.append(item)
        out_sections.append({"title": sec.title, "entries": entries})

    return {
        "name": name,
        "location": location,
        "contact": links_dict(contacts),
        "sections": out_sections,
        "meta": {
            "source": source,
            "version": version or None,
            "generated": date.today().isoformat(),
            "variant": "public" if public else "standard",
            "generator": "scripts/tex_to_formats.py",
        },
    }


HTML_STYLE = """
body{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.55;color:#1a1a1a;background:#fff}
h1{font-size:2.4rem;margin:0 0 .3rem}h2{font-size:1.15rem;text-transform:uppercase;letter-spacing:.06em;color:#555;border-bottom:1px solid #ddd;padding-bottom:.2rem;margin-top:2rem}
h3{font-size:1.05rem;margin:1.2rem 0 .2rem}.contact{color:#555}.details{color:#444;margin:.1rem 0 .4rem}
ul{padding-left:1.2rem}li{margin:.2rem 0}a{color:#1a4d99}
@media (prefers-color-scheme:dark){body{background:#121212;color:#e8e8e8}h2,.contact,.details{color:#aaa}h2{border-color:#333}a{color:#8ab4f8}}
""".strip()


def to_html(name: str, location: str, contacts: list[Link], sections: list[Section], version: str) -> str:
    e_ = html.escape
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e_(name)} – CV</title>",
        f'<meta name="author" content="{e_(name)}">',
    ]
    if version:
        parts.append(f'<meta name="version" content="{e_(version)}">')
    parts += [f"<style>{HTML_STYLE}</style>", "</head>", "<body>", "<header>", f"<h1>{e_(name)}</h1>"]
    bits = ([e_(location)] if location else []) + [
        f'<a href="{e_(c.url)}">{e_(c.text)}</a>' for c in contacts]
    if bits:
        parts.append(f'<p class="contact">{" · ".join(bits)}</p>')
    parts += ["</header>", "<main>"]
    for sec in sections:
        parts += ["<section>", f"<h2>{e_(sec.title)}</h2>"]
        for e in sec.entries:
            parts.append("<article>" if e.title else "<div>")
            if e.title:
                parts.append(f"<h3>{render_inline(e.title, 'html')}</h3>")
            det = lines_of(e.details, "html")
            if e.prose:
                parts += [f"<p>{d}</p>" for d in det]
            elif entry_as_list(e):
                parts.append("<ul>" + "".join(f"<li>{d}</li>" for d in det) + "</ul>")
            elif det:
                parts.append(f'<p class="details">{"<br>".join(det)}</p>')
            if e.bullets:
                parts.append("<ul>" + "".join(
                    f"<li>{render_inline(b, 'html').replace(chr(10), ' ')}</li>" for b in e.bullets) + "</ul>")
            if e.note:
                parts.append(f"<p><em>{render_inline(e.note, 'html')}</em></p>")
            parts.append("</article>" if e.title else "</div>")
        parts.append("</section>")
    parts += ["</main>", "</body>", "</html>"]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="cv.tex", help="cv.tex or coverletter.tex")
    ap.add_argument("--layout", default="layout.tex", help="layout file with name and contact block")
    ap.add_argument("--out-base", default=None, help="output basename (default: source stem)")
    ap.add_argument("--public", action="store_true", help="public contact details (no phone)")
    ap.add_argument("--version", default="", help="version string to embed")
    args = ap.parse_args()

    src = Path(args.source)
    out_base = args.out_base or src.stem
    name, location, contacts = parse_layout(Path(args.layout).read_text(encoding="utf-8"), args.public)
    tex = src.read_text(encoding="utf-8")

    if src.stem.startswith("coverletter"):
        cl = parse_coverletter(tex)
        if cl is None:
            print(f"{src}: no active \\coverletter block, nothing to write")
            return 0
        recipient, body = cl
        sections = [
            Section("Recipient", [Entry("", [ln for ln in re.split(r"\\\\", recipient) if ln.strip()], [], prose=True)]),
            Section("Letter", [Entry("", [ln for ln in re.split(r"\n\s*\n|\\\\", body) if ln.strip()], [], prose=True)]),
        ]
    else:
        sections = parse_cv(tex)
        if not sections:
            print(f"{src}: no \\cvsection blocks found", file=sys.stderr)
            return 1

    Path(f"{out_base}.md").write_text(to_markdown(name, location, contacts, sections), encoding="utf-8")
    Path(f"{out_base}.json").write_text(
        json.dumps(to_json(name, location, contacts, sections, src.name, args.version, args.public),
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(f"{out_base}.html").write_text(to_html(name, location, contacts, sections, args.version), encoding="utf-8")
    print(f"Wrote {out_base}.md, {out_base}.json, {out_base}.html from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
