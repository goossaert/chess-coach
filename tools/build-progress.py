#!/usr/bin/env python3
"""Build the progress dashboard (reports/progress.html) from the analysis sidecars.

Reads every analysis/*.json, distills one entry per game — accuracy, ACPL,
blunder count, per-phase accuracy, the honest Elo reading (the CLAUDE.md
step-2b display rule: flat fit → "unclear", floor fit → "≤1100", only a
peaked fit keeps its band number, plus an ACPL corroboration ballpark), and
the per-tag mistake counts (each mistake counted once, under its first tag)
— and emits reports/progress.html from progress-template.html by replacing
the marked `const PROGRESS = {...};` block. Everything else in the template
is left untouched, and the output is deterministic: running this twice in a
row is byte-identical. Fix dashboard UI issues in progress-template.html,
never in reports/progress.html.

Run it after every analyzed game (no engines, no venv needed):

    python3 tools/build-progress.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Rough rapid-pool ACPL ↔ rating ballparks (see CLAUDE.md step 2b) —
# corroboration only, never the headline number.
ACPL_BANDS = [
    (20, "~2000+"),
    (35, "~1700–2000"),
    (55, "~1400–1700"),
    (85, "~1100–1400"),
    (120, "~900–1100"),
    (None, "below ~900"),
]


def acpl_ballpark(acpl):
    for limit, label in ACPL_BANDS:
        if limit is None or acpl <= limit:
            return label


def elo_entry(elofit, acpl):
    """The honest display rule, from the sidecar's eloFit flags."""
    if not elofit:
        return None
    flat = bool(elofit.get("flat"))
    floor = bool(elofit.get("floor", elofit.get("best") == 1100))
    display = "unclear" if flat else ("≤1100" if floor else f"≈{elofit['best']}")
    entry = {"display": display, "band": elofit["best"], "flat": flat, "floor": floor}
    if acpl is not None:
        entry["note"] = f"ACPL {acpl} is typical of {acpl_ballpark(acpl)} rapid"
    return entry


def game_entry(path, data):
    stamp = path.stem
    game = data["game"]
    acc = data.get("accuracy") or {}
    quality = acc.get("quality") or {}
    phases = {
        ph: block["accuracy"]
        for ph, block in (acc.get("phases") or {}).items()
        if block.get("accuracy") is not None
    }
    tags = {}
    for mistake in data.get("mistakes", []):
        primary = (mistake.get("tags") or ["untagged"])[0]
        tags[primary] = tags.get(primary, 0) + 1
    return {
        "stamp": stamp,
        "date": stamp[:10],
        "time": stamp[11:16].replace("-", ":"),
        "label": f"{game['white']} vs {game['black']}",
        "result": game.get("result", ""),
        "userColor": game.get("userColor", ""),
        "page": f"../games/{stamp}.html",
        "accuracy": acc.get("game"),
        "acpl": acc.get("acpl"),
        "blunders": quality.get("blunders", 0),
        "mistakes": len(data.get("mistakes", [])),
        "phases": phases,
        "elo": elo_entry(data.get("eloFit"), acc.get("acpl")),
        "tags": tags,
    }


def main():
    sidecar_paths = sorted((ROOT / "analysis").glob("*.json"))
    if not sidecar_paths:
        sys.exit("no sidecars in analysis/ — nothing to build")

    progress = {
        "games": [game_entry(p, json.loads(p.read_text())) for p in sidecar_paths]
    }

    template = (ROOT / "progress-template.html").read_text()
    block = "const PROGRESS = " + json.dumps(progress, indent=2, ensure_ascii=False) + ";"
    html, n = re.subn(
        r"const PROGRESS = \{.*?\n\};", lambda _: block, template, count=1, flags=re.S
    )
    if n != 1:
        sys.exit("could not find the PROGRESS data block in progress-template.html")
    out = ROOT / "reports" / "progress.html"
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)}: {len(progress['games'])} games")


if __name__ == "__main__":
    main()
