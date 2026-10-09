#!/usr/bin/env python3
"""Build the site: content/**/*.md + template.html + static/ -> _site/.

    python build.py          # build
    python build.py serve    # build, then serve on http://localhost:8000

Layout:
    content/index.md         -> /
    content/<page>.md        -> /<page>/
    content/writing/<slug>.md -> /writing/<slug>/   (dated, listed on /writing/)
    static/**                -> copied to the site root as-is

A page's title is its first "# Heading" (the site name if it has none).
Writing entries start with their
dates, then a blank line, then the title:

    created: 2026-10-08
    updated: 2026-11-02      (optional)

    # Title
"""
import html
import re
import shutil
import sys
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template

import markdown

SITE_NAME = "Patrick Piper"
ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUT = ROOT / "_site"
TEMPLATE = Template((ROOT / "template.html").read_text())
TITLE_RE = re.compile(r"^# +(.+)$", re.MULTILINE)


def split_title(text, fallback):
    """Pull the first "# Heading" out of the markdown; return (title, rest)."""
    match = TITLE_RE.search(text)
    if not match:
        return fallback, text
    return match.group(1).strip(), text[:match.start()] + text[match.end():]


def write_page(url_path, title, body):
    """Write body into the template at _site/<url_path>/index.html."""
    out = OUT / url_path / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    page_title = title if title == SITE_NAME else f"{title} | {SITE_NAME}"
    out.write_text(TEMPLATE.substitute(title=html.escape(page_title), content=body))


def render(text):
    """Return (html, meta) where meta holds any leading "key: value" lines."""
    md = markdown.Markdown(extensions=["extra", "sane_lists", "meta"])
    body = md.convert(text)
    return body, {key: values[0] for key, values in md.Meta.items()}


def time_tag(day):
    return f'<time datetime="{day}">{day}</time>'


def build():
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(STATIC, OUT, ignore=shutil.ignore_patterns(".DS_Store"))

    for src in CONTENT.glob("*.md"):
        text = src.read_text()
        title, _ = split_title(text, SITE_NAME)
        url_path = "" if src.stem == "index" else src.stem
        write_page(url_path, title, render(text)[0])

    entries = []
    for src in (CONTENT / "writing").glob("*.md"):
        title, text = split_title(src.read_text(), src.stem)
        body, meta = render(text)
        if "created" not in meta:
            sys.exit(f"{src.relative_to(ROOT)}: missing 'created: YYYY-MM-DD' at top of file")
        created = date.fromisoformat(meta["created"]).isoformat()
        updated = date.fromisoformat(meta.get("updated", created)).isoformat()
        dates = f"Published {time_tag(created)}"
        if updated != created:
            dates += f" &middot; Updated {time_tag(updated)}"
        write_page(
            f"writing/{src.stem}",
            title,
            f'<h1>{html.escape(title)}</h1>\n<p class="meta">{dates}</p>\n{body}',
        )
        entries.append((created, src.stem, title))

    items = "\n".join(
        f'<li>{time_tag(created)} &mdash; <a href="/writing/{slug}/">{html.escape(title)}</a></li>'
        for created, slug, title in sorted(entries, reverse=True)
    )
    write_page("writing", "Writing", f'<h1>Writing</h1>\n<ul class="posts">\n{items}\n</ul>')
    print(f"Built {len(entries)} writing entries -> {OUT.relative_to(ROOT)}/")


def serve(port=8000):
    handler = partial(SimpleHTTPRequestHandler, directory=str(OUT))
    print(f"Serving http://localhost:{port} (Ctrl-C to stop)")
    ThreadingHTTPServer(("localhost", port), handler).serve_forever()


if __name__ == "__main__":
    build()
    if sys.argv[1:] == ["serve"]:
        serve()
