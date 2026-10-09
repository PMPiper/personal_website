# personal_website

Personal site. No framework: `build.py` turns markdown into HTML
using one template and one dependency (`markdown`).

## Setup

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Build and preview

```sh
.venv/bin/python build.py serve   # builds to _site/, serves http://localhost:8000
```

Re-run after editing; there is no file watcher.

## Layout

| Path                     | Becomes                         |
| ------------------------ | ------------------------------- |
| `content/index.md`       | `/`                             |
| `content/<page>.md`      | `/<page>/`                      |
| `content/writing/<slug>.md` | `/writing/<slug>/`, listed on `/writing/` |
| `static/**`              | copied to the site root as-is   |
| `template.html`          | the HTML and CSS around every page |

## Adding a post or paper

Add `content/writing/my-post.md`:

```markdown
created: 2026-10-08
updated: 2026-11-02

# Title

Body...
```

`created` is required, `updated` is optional, and the blank line before the
title matters. Put images in `static/images/` and PDFs in `static/files/`,
and link them with absolute paths (`/images/foo.png`). A paper is just an
entry whose body links to its PDF.

The nav links live in `template.html`. The resume's "last updated" date is
in `content/index.md`.

## License

Code is MIT; content is all rights reserved. See `LICENSE`.
