#!/usr/bin/env python3
"""Regenerate the data-driven parts of the recurring-mistakes trend report.

Reads every analysis/*.json sidecar and rebuilds the generated regions of the
newest reports/*-recurring-mistakes-and-lichess-study-plan .md + .html pair
IN PLACE — the curated prose and the Lichess link checklists live outside the
marked regions and are preserved verbatim (same replace-only-inside-markers
discipline as games/index.html), and the .html checkbox keys stay URL-derived
so ticks survive every regeneration. Running it twice is byte-identical.

Marked regions (identical markers in both files):

    <!-- TREND:META -->        the player / games-analyzed / engine line
    <!-- TREND:SCOREBOARD -->  per-game scoreboard + footnote definitions
    <!-- TREND:CATEGORIES -->  mistake categories ordered by aggregate win% cost
    <!-- TREND:EVIDENCE tags=a,b -->  per-section evidence tables (each sidecar
                               mistake appears once, under its FIRST tag)
    <!-- TREND:SOURCES -->     the source-files table

Cadence (see CLAUDE.md): regenerate on request, and suggest a run whenever
three or more games have accumulated since the report's games-analyzed count.

Run (plain python3, no venv or engines needed):

    python3 tools/build-trend-report.py
"""

import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUFFIX = "-recurring-mistakes-and-lichess-study-plan"
MINUS = "−"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

MARK = re.compile(
    r"<!-- TREND:([A-Z]+)((?: [^>]*?)?) -->\n.*?<!-- END TREND:\1 -->", re.S)


def san_label(ply, san):
    return f"{ply // 2 + 1}{'…' if ply % 2 else '.'}{san}"


def glyph(drop):
    return "??" if drop >= 30 else "?" if drop >= 20 else "?!" if drop >= 10 else ""


def fmt_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {d}"


def is_mate_for_user(ev):
    return isinstance(ev, dict) and (
        ev.get("mate", 0) > 0 or (ev.get("mate") == 0 and ev.get("winner") == "user"))


def load_games():
    games = []
    for path in sorted((ROOT / "analysis").glob("*.json")):
        d = json.loads(path.read_text())
        d["_stamp"] = path.stem
        games.append(d)
    if not games:
        sys.exit("no sidecars in analysis/ — nothing to build")
    return games


def user_name(d):
    g = d["game"]
    return g["white"] if g["userColor"] == "white" else g["black"]


def opponent_name(d):
    g = d["game"]
    return g["black"] if g["userColor"] == "white" else g["white"]


def user_result(d):
    g = d["game"]
    won = "1-0" if g["userColor"] == "white" else "0-1"
    lost = "0-1" if g["userColor"] == "white" else "1-0"
    return "Won" if g["result"] == won else "Lost" if g["result"] == lost \
        else "Draw" if g["result"] == "1/2-1/2" else "?"


def short_label(d):
    s = d["_stamp"]
    side = "W" if d["game"]["userColor"] == "white" else "B"
    return f"{s[5:10]} {s[11:13]}:{s[14:16]} ({side})"


def long_label(d):
    s = d["_stamp"]
    return f"{s[:10]} {s[11:13]}:{s[14:16]} vs {opponent_name(d)}"


def peak_eval(d):
    mx = None
    mate = False
    for p in d["plies"]:
        for ev in (p["evalBefore"], p["evalAfter"]):
            if is_mate_for_user(ev):
                mate = True
            elif not isinstance(ev, dict):
                mx = ev if mx is None else max(mx, ev)
    if mate:
        return "mate on the board"
    if mx is None:
        return "—"
    return f"{mx:+.1f}".replace("-", MINUS)


# --------------------------------------------------------------------------
# Table rendering — one row model, two output formats.
# --------------------------------------------------------------------------

def md_cell(text):
    return str(text).replace("|", "\\|")


def render_table(fmt, header, rows):
    """rows contain plain strings or ('link', href, text) tuples."""
    def cell(c, html):
        if isinstance(c, tuple) and c[0] == "link":
            return (f'<a href="{c[1]}">{escape(c[2])}</a>' if html
                    else f"[{md_cell(c[2])}]({c[1]})")
        if isinstance(c, tuple) and c[0] == "code":
            return f"<code>{escape(c[1])}</code>" if html else f"`{c[1]}`"
        if isinstance(c, tuple) and c[0] == "strong":
            return f"<strong>{escape(c[1])}</strong>" if html else f"**{c[1]}**"
        return escape(str(c)) if html else md_cell(c)

    if fmt == "html":
        out = ['<div class="table-wrap"><table>']
        out.append("<thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in header)
                   + "</tr></thead>")
        out.append("<tbody>")
        for r in rows:
            out.append("<tr>" + "".join(f"<td>{cell(c, True)}</td>" for c in r) + "</tr>")
        out.append("</tbody></table></div>")
        return "\n".join(out) + "\n"
    out = ["| " + " | ".join(header) + " |",
           "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(cell(c, False) for c in r) + " |")
    return "\n".join(out) + "\n"


def para(fmt, md_text, html_text):
    return (html_text + "\n") if fmt == "html" else (md_text + "\n")


# --------------------------------------------------------------------------
# Region content.
# --------------------------------------------------------------------------

def region_meta(fmt, games):
    names = {}
    for d in games:
        names[user_name(d)] = names.get(user_name(d), 0) + 1
    player = sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    dates = sorted(d["_stamp"][:10] for d in games)   # stamps are always ISO
    span = f"{fmt_date(dates[0])} – {fmt_date(dates[-1])}, {dates[-1][:4]}"
    md = (f"**Player:** {player} · **Games analyzed:** {len(games)} ({span}) · "
          "**Engine:** Stockfish, depth 20, every move you played · "
          "**Evals:** always from your perspective (positive = good for you)")
    html = (f"<p><strong>Player:</strong> {escape(player)} · "
            f"<strong>Games analyzed:</strong> {len(games)} ({escape(span)}) · "
            "<strong>Engine:</strong> Stockfish, depth 20, every move you played · "
            "<strong>Evals:</strong> always from your perspective "
            "(positive = good for you)</p>")
    return para(fmt, md, html)


def region_scoreboard(fmt, games):
    header = ["Game", "You played", "Result for you", "ACPL¹", "Accuracy",
              "Mistakes²", "Blunders³", "Peak eval"]
    rows = []
    for d in games:
        acc = d.get("accuracy") or {}
        q = acc.get("quality") or {}
        res = user_result(d)
        rows.append([
            ("link", f"../games/{d['_stamp']}.html", long_label(d)),
            d["game"]["userColor"].capitalize(),
            ("strong", res) if res == "Won" else res,
            acc.get("acpl", "—"),
            f"{acc['game']:.0f}%" if acc.get("game") is not None else "—",
            q.get("mistakes", "—"),
            q.get("blunders", "—"),
            peak_eval(d),
        ])
    table = render_table(fmt, header, rows)
    foot = ("¹ average centipawn loss vs. Stockfish's best move (each loss clamped "
            "to [0, 1000] cp). ² moves dropping your win probability by ≥20 points "
            "(?). ³ moves dropping it by ≥30 points (??).")
    return table + para(fmt, "\n" + foot, f"<p>{foot}</p>")


def mistakes_by_first_tag(games):
    by_tag = {}
    for d in games:
        for mk in d.get("mistakes") or []:
            tag = (mk.get("tags") or ["untagged"])[0]
            by_tag.setdefault(tag, []).append((d, mk))
    return by_tag


def drop(mk):
    return mk["winBefore"] - mk["winAfter"]


def region_categories(fmt, games):
    by_tag = mistakes_by_first_tag(games)
    order = sorted(by_tag.items(), key=lambda kv: (-sum(drop(m) for _, m in kv[1]),
                                                   kv[0]))
    header = ["Category", "Mistakes", "Games", "Win% lost (total)⁴",
              "Worst single moment"]
    rows = []
    for tag, entries in order:
        worst_d, worst_m = max(entries, key=lambda e: drop(e[1]))
        cost = sum(drop(m) for _, m in entries)
        rows.append([
            ("code", tag),
            len(entries),
            len({d["_stamp"] for d, _ in entries}),
            f"{MINUS}{cost:.0f}" if cost >= 0.5 else "≈0 (missed wins, not losses)",
            ("link", f"../games/{worst_d['_stamp']}.html",
             f"{san_label(worst_m['ply'], worst_m['played'])}"
             f"{glyph(drop(worst_m))} ({short_label(worst_d)})"),
        ])
    table = render_table(fmt, header, rows)
    foot = ("⁴ each analyzed mistake counted once, under its first taxonomy tag; "
            "cost = win-probability points lost on that move (winBefore − winAfter "
            "from the sidecar).")
    return table + para(fmt, "\n" + foot, f"<p>{foot}</p>")


def region_evidence(fmt, games, tags):
    by_tag = mistakes_by_first_tag(games)
    entries = [e for t in tags for e in by_tag.get(t, [])]
    entries.sort(key=lambda e: (-drop(e[1]), e[0]["_stamp"], e[1]["ply"]))
    if not entries:
        line = "*(no tagged examples in the analyzed games yet)*"
        return para(fmt, line, "<p><em>(no tagged examples in the analyzed games yet)</em></p>")
    header = ["Game", "Move", "What happened", "Your win%", "Cost"]
    rows = []
    for d, mk in entries:
        rows.append([
            ("link", f"../games/{d['_stamp']}.html", short_label(d)),
            f"{san_label(mk['ply'], mk['played'])}{glyph(drop(mk))}",
            mk.get("title", ""),
            f"{round(mk['winBefore'])}% → {round(mk['winAfter'])}%",
            mk.get("swing", ""),
        ])
    return render_table(fmt, header, rows)


def region_sources(fmt, games):
    header = ["#", "Source PGN (pgn/)", "Coach page (games/)", "You played", "Result"]
    rows = []
    for i, d in enumerate(games, 1):
        res = user_result(d).lower()
        stamp = d["_stamp"]
        rows.append([
            i,
            ("link", f"../pgn/{stamp}.txt", f"{stamp}.txt"),
            ("link", f"../games/{stamp}.html", f"{stamp}.html"),
            d["game"]["userColor"].capitalize(),
            f"{d['game']['result'].replace('-', '–')} ({res})",
        ])
    return render_table(fmt, header, rows)


def render_region(kind, args, fmt, games):
    if kind == "META":
        return region_meta(fmt, games)
    if kind == "SCOREBOARD":
        return region_scoreboard(fmt, games)
    if kind == "CATEGORIES":
        return region_categories(fmt, games)
    if kind == "EVIDENCE":
        m = re.search(r"tags=([a-z\-,]+)", args)
        if not m:
            sys.exit(f"EVIDENCE region without tags= argument: {args!r}")
        return region_evidence(fmt, games, m.group(1).split(","))
    if kind == "SOURCES":
        return region_sources(fmt, games)
    sys.exit(f"unknown TREND region {kind!r}")


def rebuild(text, fmt, games):
    def sub(m):
        kind, args = m.group(1), m.group(2).strip()
        body = render_region(kind, args, fmt, games)
        head = f"<!-- TREND:{kind}" + (f" {args}" if args else "") + " -->"
        return f"{head}\n{body}<!-- END TREND:{kind} -->"
    return MARK.subn(sub, text)


def main():
    md_paths = sorted(ROOT.glob(f"reports/*{SUFFIX}.md"))
    if not md_paths:
        sys.exit(f"no reports/*{SUFFIX}.md found")
    md_path = md_paths[-1]
    html_path = md_path.with_suffix(".html")
    if not html_path.exists():
        sys.exit(f"missing html half: {html_path}")

    games = load_games()
    total_mistakes = sum(len(d.get("mistakes") or []) for d in games)
    for path, fmt in ((md_path, "md"), (html_path, "html")):
        text = path.read_text()
        new, n = rebuild(text, fmt, games)
        if n == 0:
            sys.exit(f"no TREND regions found in {path.name}")
        path.write_text(new)
        print(f"wrote {path.relative_to(ROOT)}: {n} regions, "
              f"{len(games)} games, {total_mistakes} mistakes")


if __name__ == "__main__":
    main()
