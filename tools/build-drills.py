#!/usr/bin/env python3
"""Build the personal drill deck (drills/index.html) from the analysis sidecars.

Two jobs, in order:

1. Backfill `retry` grading data into any sidecar mistake that lacks it
   (part-1 sidecars predate the field): full legal-move list via python-chess,
   `solutions` = engine best + humanBest (deduped), `acceptable` = moves from a
   Stockfish multipv-5 probe (depth 18) whose eval stays within 0.5 pawns of
   best (evals clamped to ±10 pawns, mates through mate_score) minus the
   solutions and the move actually played. The computed object is written back
   into the sidecar so the probe runs once ever.
2. Emit `drills/index.html` from `drills-template.html` by replacing the
   marked `const DRILLS = [...];` block — one entry per sidecar mistake.
   Everything else in the template is left untouched, and the output is
   deterministic: running this twice in a row is byte-identical.

Run with the analysis venv (system pip can't install python-chess):

    /tmp/chess-venv/bin/python tools/build-drills.py

Stockfish (/usr/games/stockfish) is only needed when a sidecar still lacks
`retry` data.
"""

import json
import re
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
STOCKFISH = "/usr/games/stockfish"
MATE_SCORE = 100000
CLAMP_CP = 1000          # ±10 pawns, same clamp as the human-findable scan
ACCEPT_WINDOW_CP = 50    # "acceptable" = within 0.5 pawns of best
PROBE_DEPTH = 18


def clamped_cp(info, turn):
    cp = info["score"].pov(turn).score(mate_score=MATE_SCORE)
    return max(-CLAMP_CP, min(CLAMP_CP, cp))


def compute_retry(mistake, engine):
    board = chess.Board(mistake["fenBefore"])
    legal = sorted(m.uci() for m in board.legal_moves)

    solutions = [mistake["bestUci"]]
    human = mistake.get("humanBestUci")
    if human and human not in solutions:
        solutions.append(human)
    for uci in solutions:
        if uci not in legal:
            raise ValueError(f"solution {uci} not legal in {mistake['fenBefore']}")

    infos = engine.analyse(
        board, chess.engine.Limit(depth=PROBE_DEPTH), multipv=min(5, len(legal))
    )
    best_cp = max(clamped_cp(info, board.turn) for info in infos)
    acceptable = sorted(
        info["pv"][0].uci()
        for info in infos
        if clamped_cp(info, board.turn) >= best_cp - ACCEPT_WINDOW_CP
        and info["pv"][0].uci() not in solutions
        and info["pv"][0].uci() != mistake["playedUci"]
    )
    return {
        "fen": mistake["fenBefore"],
        "solutions": solutions,
        "acceptable": acceptable,
        "legal": legal,
    }


def backfill_retry(sidecars):
    engine = None
    changed = []
    try:
        for path, data in sidecars:
            dirty = False
            for mistake in data["mistakes"]:
                if "retry" in mistake:
                    continue
                if engine is None:
                    import chess.engine
                    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH)
                    engine.configure({"Threads": 3, "Hash": 512})
                mistake["retry"] = compute_retry(mistake, engine)
                dirty = True
            if dirty:
                # Same serialization the part-1 backfill used — byte-stable.
                path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
                changed.append(path.name)
    finally:
        if engine is not None:
            engine.quit()
    return changed


def build_drills(sidecars):
    drills = []
    for path, data in sidecars:
        stamp = path.stem
        game = data["game"]
        label = f"{game['white']} vs {game['black']} · {game['date']}"
        for mistake in data["mistakes"]:
            retry = mistake["retry"]
            side = "white" if retry["fen"].split()[1] == "w" else "black"
            drill = {
                "id": f"{stamp}:{mistake['ply']}",
                "fen": retry["fen"],
                "side": side,
                "moveNo": mistake["ply"] // 2 + 1,
                "solutions": retry["solutions"],
                "acceptable": retry["acceptable"],
                "legal": retry["legal"],
                "played": mistake["played"],
                "best": mistake["best"],
            }
            if len(retry["solutions"]) > 1:
                # SAN for the human-findable solution; pre-Maia pages have no
                # humanBest SAN in the mistake, so derive it from the UCI
                drill["humanBest"] = mistake.get("humanBest") or chess.Board(
                    retry["fen"]
                ).san(chess.Move.from_uci(retry["solutions"][1]))
            drill["tags"] = mistake.get("tags", [])
            drill["title"] = mistake.get("title", "")
            takeaways = mistake.get("takeaways") or []
            if takeaways:
                drill["lesson"] = takeaways[0]["lesson"]
            drill["game"] = f"../games/{stamp}.html"
            drill["gameLabel"] = label
            drills.append(drill)
    drills.sort(key=lambda d: (d["id"].split(":")[0], int(d["id"].split(":")[1])))
    return drills


def main():
    sidecar_paths = sorted((ROOT / "analysis").glob("*.json"))
    if not sidecar_paths:
        sys.exit("no sidecars in analysis/ — nothing to build")
    sidecars = [(p, json.loads(p.read_text())) for p in sidecar_paths]

    changed = backfill_retry(sidecars)
    for name in changed:
        print(f"backfilled retry: {name}")

    drills = build_drills(sidecars)
    template = (ROOT / "drills-template.html").read_text()
    block = "const DRILLS = " + json.dumps(drills, indent=2, ensure_ascii=False) + ";"
    html, n = re.subn(
        r"const DRILLS = \[.*?\n\];", lambda _: block, template, count=1, flags=re.S
    )
    if n != 1:
        sys.exit("could not find the DRILLS data block in drills-template.html")
    out = ROOT / "drills" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)}: {len(drills)} drills from {len(sidecars)} games")


if __name__ == "__main__":
    main()
