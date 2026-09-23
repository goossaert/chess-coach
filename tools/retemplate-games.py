#!/usr/bin/env python3
"""Roll the current template.html forward into every generated game page.

Generated pages embed a full copy of the template's markup, CSS, and scripts,
so a template fix only reaches pages built after it. This rebuilds each live
page (games/*.html except index.html; games/archive/ is never touched) from a
fresh copy of template.html with the page's own `const GAME = {…};` block and
`<title>` spliced in verbatim — exactly what workflow step 4 does, no engines,
no data changes. After writing, it re-extracts both from the new file and
asserts they are byte-identical to the originals.

    python3 tools/retemplate-games.py           # update pages, one line each
    python3 tools/retemplate-games.py --check   # write nothing; exit 1 on drift

Idempotent: a second run reports every page `unchanged`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_RE = re.compile(r"const GAME = \{.*?\n\};", re.S)
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)


def extract(html, regex, what, name):
    matches = regex.findall(html)
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one {what}, found {len(matches)}")
    return matches[0]


def rebuild(template, page_html, name):
    game = extract(page_html, GAME_RE, "GAME block", name)
    title = extract(page_html, TITLE_RE, "<title>", name)
    # replacement functions, so backslashes in the data stay literal
    out, n = GAME_RE.subn(lambda _: game, template, count=1)
    if n != 1:
        raise ValueError(f"{name}: GAME block substitution matched {n} times")
    out, n = TITLE_RE.subn(lambda _: title, out, count=1)
    if n != 1:
        raise ValueError(f"{name}: <title> substitution matched {n} times")
    # prove the data went through untouched
    if extract(out, GAME_RE, "GAME block", name) != game:
        raise ValueError(f"{name}: GAME block changed during rebuild")
    if extract(out, TITLE_RE, "<title>", name) != title:
        raise ValueError(f"{name}: <title> changed during rebuild")
    return out


def main():
    check = "--check" in sys.argv[1:]
    template = (ROOT / "template.html").read_text()
    pages = sorted(p for p in (ROOT / "games").glob("*.html") if p.name != "index.html")
    stale = failed = 0
    for page in pages:
        name = page.relative_to(ROOT)
        html = page.read_text()
        try:
            new = rebuild(template, html, name)
        except ValueError as e:
            print(f"error      {e}")
            failed += 1
            continue
        if new == html:
            print(f"unchanged  {name}")
            continue
        stale += 1
        if check:
            print(f"stale      {name}")
        else:
            page.write_text(new)
            print(f"updated    {name}")
    if failed or (check and stale):
        sys.exit(1)


if __name__ == "__main__":
    main()
