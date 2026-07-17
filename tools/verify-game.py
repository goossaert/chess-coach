#!/usr/bin/env python3
"""Consolidated page verification — the whole CLAUDE.md step-6 checklist in
one call.

Drives one headless-Chromium load of the generated page (via the companion
tools/verify-game.cjs, a single subprocess) for every in-page check —
error banner, replay total/placement, mistake-card clicks, arrows + legend on
every position, field-presence iff rules, eval graph, retry mode — and runs
every data-side check with python-chess in this process: PGN/movesSan parity,
move + arrow legality, humanBest eval re-checks, win%/accuracy math, tag
vocabulary, drill-link provenance, retry-object soundness, and full sidecar
cross-checks. Every assertion in CLAUDE.md step 6 runs; nothing was cut.

Output: one PASS/FAIL summary. A healthy page prints a single line
("all checks passed …"); failures print one line each with enough detail
(which check, which ply) to debug directly.

Usage (venv python — needs python-chess; Stockfish for the humanBest
re-checks):

    /tmp/chess-venv/bin/python tools/verify-game.py games/<stamp>.html
    /tmp/chess-venv/bin/python tools/verify-game.py template.html --page-only

--page-only skips the PGN/sidecar/engine cross-checks (for template demos);
--no-engine skips only the Stockfish humanBest re-check probes.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import chess
import chess.engine
import chess.polyglot

ROOT = Path(__file__).resolve().parent.parent
STOCKFISH = "/usr/games/stockfish"
NODE_PATH = "/opt/node22/lib/node_modules"
MATE_SCORE = 100000
CLAMP_CP = 1000
RECHECK_DEPTH = 18
HUMAN_WINDOW_CP = 50
NOISE_SLACK_CP = 15       # re-running the engine never reproduces the original
                          #   evals exactly; only flag humanBest when it misses
                          #   the 0.5-pawn window by more than this
TAGS = {
    "hanging-piece", "unsafe-capture", "wrong-recapture", "missed-tactic",
    "missed-mate", "slow-mate", "king-safety", "unsafe-king-move",
    "pawn-break-timing", "conversion-drift", "promotion-race",
    "endgame-technique", "opening-principle", "time-trouble",
}

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), str(detail)))


def win_pct(cp):
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def cp_of(ev):
    """Clamped centipawns from a sidecar eval value (number or mate object)."""
    if isinstance(ev, dict):
        if ev.get("mate", 0) > 0 or ev.get("winner") == "user":
            return CLAMP_CP
        return -CLAMP_CP
    return max(-CLAMP_CP, min(CLAMP_CP, round(ev * 100)))


def parse_pgn_moves(path):
    import chess.pgn
    with open(path, encoding="utf-8") as f:
        game = chess.pgn.read_game(f)
    if game is None:
        return None
    board = chess.Board()
    sans = []
    for mv in game.mainline_moves():
        sans.append(board.san(mv))
        board.push(mv)
    return sans, board


def browser_pass(page_path):
    env = dict(os.environ)
    env.setdefault("NODE_PATH", NODE_PATH)
    r = subprocess.run(
        ["node", str(ROOT / "tools" / "verify-game.cjs"), str(page_path)],
        capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        sys.exit(f"verify-game.cjs failed:\n{r.stderr.strip()[-2000:]}")
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("page", help="generated page (games/<stamp>.html)")
    ap.add_argument("--page-only", action="store_true",
                    help="skip PGN/sidecar/engine cross-checks (template demos)")
    ap.add_argument("--no-engine", action="store_true",
                    help="skip the Stockfish humanBest re-check probes")
    args = ap.parse_args()

    page_path = Path(args.page)
    if not page_path.exists():
        sys.exit(f"no such file: {page_path}")
    stamp = page_path.stem

    out = browser_pass(page_path)
    checks.extend((r["name"], r["pass"], r.get("detail", "")) for r in out["results"])
    check("no page errors", not out["pageErrors"], "; ".join(out["pageErrors"][:3]))

    G = out["game"]
    moves_san = G["movesSan"]
    mistakes = G.get("mistakes") or []
    notes = G.get("moveNotes") or []
    is_maia = out["isMaia"]
    user_white = G.get("playerColor") == "white"

    # ---- replay with python-chess: positions before every ply ------------
    board = chess.Board()
    pos_before = []
    replay_err = None
    for i, san in enumerate(moves_san):
        pos_before.append(board.copy(stack=False))
        try:
            board.push_san(san)
        except ValueError as e:
            replay_err = f"ply {i} ({san}): {e}"
            break
    check("movesSan replays legally", replay_err is None, replay_err)
    if replay_err:
        report()
    if out["placement"] is not None:
        check("placement(total) matches python-chess",
              out["placement"] == board.board_fen(),
              f"{out['placement']} vs {board.board_fen()}")

    def user_ply(p):
        return (p % 2 == 0) == user_white

    # ---- mistakes: ply alignment, legality, arrows -----------------------
    ann = {}
    for n in notes:
        ann[n["ply"]] = n
    for mk in mistakes:
        ann[mk["ply"]] = mk
    for i, mk in enumerate(mistakes):
        ply = mk["ply"]
        pos = pos_before[ply] if 0 <= ply < len(pos_before) else None
        check(f"mistake {i} ply in range", pos is not None, ply)
        if pos is None:
            continue
        check(f"mistake {i} played matches movesSan[{ply}]",
              moves_san[ply] == mk["played"], f"{moves_san[ply]} vs {mk['played']}")
        for field, arrow_field in (("played", "playedArrow"), ("best", "bestArrow"),
                                   ("humanBest", "humanBestArrow")):
            if field not in mk:
                continue
            try:
                mv = pos.parse_san(mk[field])
            except ValueError as e:
                check(f"mistake {i} {field} legal", False, f"{mk[field]}: {e}")
                continue
            check(f"mistake {i} {field} legal", True)
            if arrow_field in mk:
                uci = mv.uci()
                check(f"mistake {i} {arrow_field} matches move",
                      mk[arrow_field] == [uci[0:2], uci[2:4]],
                      f"{mk[arrow_field]} vs {uci}")

    # ---- moveNotes: coverage + legality ----------------------------------
    if notes:      # the coverage rule applies to pages that carry moveNotes
        uncovered = [p for p in range(len(moves_san)) if user_ply(p) and p not in ann]
        check("every user ply covered by moveNotes or mistakes", not uncovered,
              f"plies {uncovered[:8]}")
    bad = []
    for n in notes:
        pos = pos_before[n["ply"]]
        for field, arrow_field in (("best", "bestArrow"), ("humanBest", "humanBestArrow")):
            if field not in n:
                continue
            try:
                mv = pos.parse_san(n[field])
            except ValueError as e:
                bad.append(f"ply {n['ply']} {field} {n[field]}: {e}")
                continue
            if arrow_field in n and n[arrow_field] != [mv.uci()[0:2], mv.uci()[2:4]]:
                bad.append(f"ply {n['ply']} {arrow_field} mismatch")
    check("moveNotes moves legal, arrows match", not bad, " | ".join(bad[:4]))

    # ---- Maia-page completeness + field formats --------------------------
    if is_maia:
        missing = [n["ply"] for n in notes if "humanBest" not in n or "humanBestArrow" not in n]
        missing += [m["ply"] for m in mistakes if "humanBest" not in m or "humanBestArrow" not in m]
        check("humanBest on every note and mistake (Maia page)", not missing,
              f"plies {missing[:8]}")
        pct = re.compile(r"^(<1|\d{1,3}(\.\d+)?)%$")
        bad = []
        for m in mistakes:
            for f in ("playedPopularity", "bestFindability", "humanBestFindability"):
                if f in m and not pct.match(m[f]):
                    bad.append(f"ply {m['ply']} {f}={m[f]!r}")
            epl = m.get("expectedPointsLost")
            if epl is not None and not re.match(r"^[−+-]?\d+\.\d\d$", epl):
                bad.append(f"ply {m['ply']} expectedPointsLost={epl!r}")  # "±0.00" must be omitted
        check("percentages / expectedPointsLost well-formed", not bad, " | ".join(bad[:4]))

    # ---- tags vocabulary + drill-link provenance -------------------------
    bad = [t for m in mistakes for t in (m.get("tags") or []) if t not in TAGS]
    check("mistake tags from the taxonomy", not bad, bad[:5])
    links = json.loads((ROOT / "tools" / "drill-links.json").read_text())
    known_urls = {d["url"] for v in links.values() if isinstance(v, list) for d in v}
    bad = [d["url"] for m in mistakes for d in (m.get("drillLinks") or [])
           if d["url"] not in known_urls]
    check("drill links come from tools/drill-links.json", not bad, bad[:3])

    # ---- retry objects (page side) ---------------------------------------
    for i, mk in enumerate(mistakes):
        r = mk.get("retry")
        if not r:
            continue
        pos = pos_before[mk["ply"]]
        legal = sorted(m.uci() for m in pos.legal_moves)
        check(f"retry {i} fen matches position before ply", r["fen"] == pos.fen(),
              f"{r['fen']} vs {pos.fen()}")
        check(f"retry {i} legal list exact", r["legal"] == legal)
        sols, acc = set(r["solutions"]), set(r.get("acceptable") or [])
        check(f"retry {i} solutions ⊆ legal", sols <= set(legal), sols - set(legal))
        check(f"retry {i} acceptable ⊆ legal", acc <= set(legal), acc - set(legal))
        check(f"retry {i} solutions ∩ acceptable empty", not (sols & acc), sols & acc)
        best_uci = pos.parse_san(mk["best"]).uci()
        check(f"retry {i} solutions contain best", best_uci in sols,
              f"{best_uci} not in {sorted(sols)}")
        played_uci = pos.parse_san(mk["played"]).uci()
        check(f"retry {i} excludes the played move",
              played_uci not in sols and played_uci not in acc, played_uci)

    # ---- evals series -----------------------------------------------------
    if G.get("evals") is not None:
        ev = G["evals"]
        check("evals has one entry per half-move", len(ev) == len(moves_san),
              f"{len(ev)} vs {len(moves_san)}")
        check("evals within [0, 100]", all(0 <= v <= 100 for v in ev))

    # ---- timeSpent series --------------------------------------------------
    if G.get("timeSpent") is not None:
        ts = G["timeSpent"]
        check("timeSpent has one entry per half-move", len(ts) == len(moves_san),
              f"{len(ts)} vs {len(moves_san)}")
        check("timeSpent values are non-negative numbers",
              all(isinstance(v, (int, float)) and v >= 0 for v in ts))

    # ---- highlights ---------------------------------------------------------
    mistake_plies = {m["ply"] for m in mistakes}
    for i, hl in enumerate(G.get("highlights") or []):
        ply = hl["ply"]
        ok = 0 <= ply < len(moves_san)
        check(f"highlight {i} ply in range", ok, ply)
        if not ok:
            continue
        check(f"highlight {i} move matches movesSan[{ply}]",
              moves_san[ply] == hl["move"], f"{moves_san[ply]} vs {hl['move']}")
        check(f"highlight {i} on a user move", user_ply(ply), ply)
        check(f"highlight {i} not on a mistake ply", ply not in mistake_plies, ply)
        if hl.get("arrow"):
            uci = pos_before[ply].parse_san(hl["move"]).uci()
            check(f"highlight {i} arrow matches the played move",
                  hl["arrow"] == [uci[0:2], uci[2:4]], f"{hl['arrow']} vs {uci}")

    # ---- opening report -----------------------------------------------------
    orep = G.get("openingReport")
    if orep:
        bep = orep.get("bookExitPly")
        if bep is not None:
            check("openingReport bookExitPly in range", 0 <= bep <= len(moves_san), bep)
            book_path = ROOT / "tools" / "book" / "gm2001.bin"
            if book_path.exists() and 0 <= bep <= len(moves_san):
                with chess.polyglot.open_reader(book_path) as reader:
                    b = chess.Board()
                    exit_ply = len(moves_san)
                    for i, san in enumerate(moves_san):
                        mv = b.parse_san(san)
                        if not any(e.move == mv for e in reader.find_all(b)):
                            exit_ply = i
                            break
                        b.push(mv)
                check("bookExitPly matches tools/book/gm2001.bin", bep == exit_ply,
                      f"page {bep} vs book {exit_ply}")
        url = orep.get("explorerUrl")
        if url:
            check("openingReport explorerUrl is a lichess.org URL",
                  url.startswith("https://lichess.org/"), url)

    if args.page_only:
        report()

    # ---- PGN parity -------------------------------------------------------
    pgn_path = ROOT / "pgn" / f"{stamp}.txt"
    check("pgn source exists", pgn_path.exists(), pgn_path)
    if pgn_path.exists():
        parsed = parse_pgn_moves(pgn_path)
        check("pgn parses", parsed is not None)
        if parsed:
            sans, _ = parsed
            check("movesSan matches the PGN", sans == moves_san,
                  f"{len(sans)} pgn vs {len(moves_san)} page moves")

    # ---- sidecar cross-checks --------------------------------------------
    side_path = ROOT / "analysis" / f"{stamp}.json"
    check("sidecar exists", side_path.exists(), side_path)
    if side_path.exists():
        d = json.loads(side_path.read_text())
        plies = d["plies"]
        check("sidecar has one entry per half-move", len(plies) == len(moves_san),
              f"{len(plies)} vs {len(moves_san)}")
        bad = []
        b = chess.Board()
        for p in plies:
            if p["fenBefore"] != b.fen():
                bad.append(f"ply {p['ply']}: fenBefore mismatch")
                break
            try:
                mv = b.parse_san(p["san"])
            except ValueError as e:
                bad.append(f"ply {p['ply']} ({p['san']}): {e}")
                break
            if mv.uci() != p["uci"]:
                bad.append(f"ply {p['ply']}: uci {p['uci']} vs {mv.uci()}")
            b.push(mv)
        check("sidecar plies replay legally with matching FENs/UCIs", not bad, bad[:3])

        bad = []
        for p in plies:
            for k_ev, k_win in (("evalBefore", "winBefore"), ("evalAfter", "winAfter")):
                w = round(win_pct(cp_of(p[k_ev])), 1)
                if abs(w - p[k_win]) > 0.05001:
                    bad.append(f"ply {p['ply']} {k_win}: {p[k_win]} vs {w}")
            if p.get("user") and "swing" in p:
                sw = round((cp_of(p["evalAfter"]) - cp_of(p["evalBefore"])) / 100, 2)
                if abs(sw - p["swing"]) > 0.005001:
                    bad.append(f"ply {p['ply']} swing: {p['swing']} vs {sw}")
        check("sidecar win%/swing follow the step-2c formulas", not bad, bad[:4])

        if G.get("evals") is not None:
            bad = [i for i, (v, p) in enumerate(zip(G["evals"], plies))
                   if abs(v - p["winAfter"]) > 0.05001]
            check("page evals equal sidecar winAfter", not bad, f"plies {bad[:6]}")

        smks = d.get("mistakes") or []
        check("sidecar mistake count matches page", len(smks) == len(mistakes),
              f"{len(smks)} vs {len(mistakes)}")
        for i, (sm, pm) in enumerate(zip(smks, mistakes)):
            check(f"sidecar mistake {i} matches page (ply/played/best)",
                  sm.get("ply") == pm["ply"] and sm.get("played") == pm["played"]
                  and sm.get("best") == pm["best"],
                  f"{sm.get('ply')}/{sm.get('played')}/{sm.get('best')} vs "
                  f"{pm['ply']}/{pm['played']}/{pm['best']}")
            bad_tags = [t for t in (sm.get("tags") or []) if t not in TAGS]
            check(f"sidecar mistake {i} tags from the taxonomy", not bad_tags, bad_tags)
            if "retry" in pm:
                check(f"sidecar mistake {i} retry identical to page",
                      sm.get("retry") == pm["retry"])

        shls = d.get("highlights") or []
        bad = [h.get("ply") for h in shls
               if not (0 <= h.get("ply", -1) < len(plies))
               or plies[h["ply"]]["san"] != h.get("move")]
        check("sidecar highlights align with sidecar plies", not bad, bad[:4])
        if G.get("highlights"):
            check("sidecar highlights match page (ply/move)",
                  [(h.get("ply"), h.get("move")) for h in shls] ==
                  [(h["ply"], h["move"]) for h in G["highlights"]])
        if orep and d.get("openingReport"):
            check("sidecar openingReport bookExitPly matches page",
                  d["openingReport"].get("bookExitPly") == orep.get("bookExitPly"),
                  f"{d['openingReport'].get('bookExitPly')} vs {orep.get('bookExitPly')}")

        fit = d.get("eloFit")
        est = G.get("estimatedElo")
        if fit and est:
            want = ("unclear" if fit.get("flat")
                    else "≤1100" if fit.get("floor", fit.get("best") == 1100)
                    else f"≈{fit['best']}")
            check("estimatedElo obeys the honest display rule", est == want,
                  f"page {est!r} vs rule {want!r} (flat={fit.get('flat')}, "
                  f"floor={fit.get('floor')})")
        if G.get("accuracy") and d.get("accuracy", {}).get("game") is not None:
            want = f"{round(d['accuracy']['game'])}%"
            check("page accuracy matches sidecar", G["accuracy"] == want,
                  f"{G['accuracy']} vs {want}")
        if G.get("acpl") is not None and d.get("accuracy", {}).get("acpl") is not None:
            check("page acpl matches sidecar", G["acpl"] == d["accuracy"]["acpl"],
                  f"{G['acpl']} vs {d['accuracy']['acpl']}")

        # Maia sanity: played-move probability well above the random baseline
        if is_maia and fit:
            band = str(fit["best"])
            probs = [p["maia"][band]["played"] for p in plies
                     if p.get("user") and p.get("maia")]
            if probs:
                avg = sum(probs) / len(probs)
                check("avg Maia probability of played moves > 0.10 at fit band",
                      avg > 0.10, f"avg {avg:.3f} — FENs/moves misaligned?")

    # ---- humanBest engine re-check (the one check that needs Stockfish) --
    if is_maia and not args.no_engine:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH)
        engine.configure({"Threads": 3, "Hash": 512})
        bad = []
        probes = 0
        try:
            for ply, entry in sorted(ann.items()):
                hb = entry.get("humanBest")
                if not hb or hb == entry.get("best"):
                    continue
                pos = pos_before[ply]
                evals = {}
                for san in (entry["best"], hb):
                    b2 = pos.copy(stack=False)
                    try:
                        b2.push(pos.parse_san(san))
                    except ValueError:
                        continue        # legality already reported above
                    info = engine.analyse(b2, chess.engine.Limit(depth=RECHECK_DEPTH))
                    pov = info["score"].pov(chess.WHITE if user_white else chess.BLACK)
                    evals[san] = max(-CLAMP_CP, min(CLAMP_CP,
                                     pov.score(mate_score=MATE_SCORE)))
                    probes += 1
                if len(evals) == 2 and (evals[hb] <
                                        evals[entry["best"]] - HUMAN_WINDOW_CP - NOISE_SLACK_CP):
                    bad.append(f"ply {ply}: {hb} {evals[hb]}cp vs best "
                               f"{entry['best']} {evals[entry['best']]}cp")
        finally:
            engine.quit()
        check(f"humanBest keeps the eval within tolerance "
              f"({probes} depth-{RECHECK_DEPTH} probes)", not bad, " | ".join(bad[:4]))

    report()


def report():
    fails = [(n, d) for n, ok, d in checks if not ok]
    if not fails:
        print(f"all checks passed ({len(checks)} checks)")
        sys.exit(0)
    for n, d in fails:
        print(f"FAIL {n}" + (f": {d}" if d else ""))
    print(f"{len(fails)} of {len(checks)} checks FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
