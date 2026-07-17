#!/usr/bin/env python3
"""Consolidated analysis pipeline — CLAUDE.md steps 2, 2b, 2c, and 2d in one call.

Runs the full per-game engine work with the exact parameters the workflow
specifies (Stockfish depth 20; depth-18 re-checks for the human-findable scan
and the multipv-5 retry probes; Maia-1 bands 1100–1900 via tools/maia/query.cjs;
the Lichess win%/accuracy/ACPL formulas; the honest Elo fit with its exclusions
and flat/floor display rule) and prints ONE JSON document to stdout with
everything steps 3/4/4b need:

- `display`      — GAME-ready display values (accuracy/acpl/moveQuality/
                   phaseAccuracy/estimatedElo/estimatedEloNote/phaseElo)
- `evals`        — the GAME `evals` win% series
- `moveNotes`    — GAME-ready per-user-move entries (best/humanBest + arrows)
- `mistakeCandidates` — ranked (mates first, then swing × recurrence weight),
                   each with GAME-ready display fields, the numeric sidecar
                   fields, and the precomputed `retry` object
- `userPlies`    — a compact per-user-move analytic summary for writing prose
- `accuracy` / `eloFit` — the sidecar blocks

It also writes the analysis sidecar DRAFT (schema, game, engine, plies with
per-band Maia numbers, accuracy, eloFit, and an empty `mistakes` array) straight
to analysis/<stamp>.json, so the heavy per-ply data never has to round-trip
through the session context — add the selected mistakes to that file in step 4b.

Usage (venv python — system pip can't install python-chess):

    /tmp/chess-venv/bin/python tools/analyze-game.py pgn/<stamp>.txt --color white

The Maia harness is started automatically (setup.sh if weights are missing,
serve.mjs if the port is closed). On any Maia failure the script degrades to a
Stockfish-only run (every Maia field omitted, `maiaError` set) per the
CLAUDE.md fallback rule. `--no-maia` forces that mode.

Analysis parameters are fixed to the CLAUDE.md spec on purpose — this script
changes how many tool calls the workflow takes, never what it computes.
"""

import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parent.parent
STOCKFISH = "/usr/games/stockfish"
NODE_PATH = "/opt/node22/lib/node_modules"
MATE_SCORE = 100000
CLAMP_CP = 1000              # ±10 pawns — win%, swing, and eval-window clamp
BANDS = list(range(1100, 2000, 100))
DEPTH_MAIN = 20              # step 2
DEPTH_RECHECK = 18           # step 2b human-findable re-check (retry probes
                             #   run inside build-drills.compute_retry, also 18)
HUMAN_WINDOW_CP = 50         # human-findable: within 0.5 pawns of best
HUMAN_MIN_PROB = 0.5         # percent; rarer candidates aren't "findable"
LOGPROB_FLOOR = 0.001        # 0.1% probability floor in the Elo fit
FLAT_SPREAD = 0.15           # nats/move; below this the fit is "flat"
ELO_EVAL_CUT = 6.0           # pawns; |eval| beyond this is a low-information
                             #   position for the fit (relaxed if a fit empties)
CANDIDATE_CAP = 20

MINUS = "−"

# Rough rapid-pool ACPL ↔ rating ballparks (corroboration only, never the
# headline number) — same table as CLAUDE.md step 2b / build-progress.py.
ACPL_BANDS = [
    (20, "~2000+"),
    (35, "~1700–2000"),
    (55, "~1400–1700"),
    (85, "~1100–1400"),
    (120, "~900–1100"),
    (None, "below ~900"),
]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------
# Step 2c math (Lichess formulas) — pure functions, no engine access.
# --------------------------------------------------------------------------

def win_pct(cp_clamped):
    """Lichess win probability from clamped centipawns (user's perspective)."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp_clamped)) - 1)


def move_accuracy(win_before, win_after):
    """Lichess per-move accuracy from the win% drop, clamped to [0, 100]."""
    drop = win_before - win_after
    acc = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, acc))


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))


def volatility_weights(win_seq, n_plies):
    """One weight per ply: population stdev of the window of the position win%
    sequence (user POV, length n_plies + 1) ending at the position after the
    move, truncated at the start, clamped to [0.5, 12]. This exact alignment
    reproduces every stored accuracy in the existing sidecars (33/33 values,
    game + phases, across all nine games)."""
    ws = max(2, min(8, n_plies // 10))
    return [max(0.5, min(12.0, stdev(win_seq[max(0, i - ws + 1):i + 2])))
            for i in range(n_plies)]


def aggregate_accuracy(accs, weights):
    """Game accuracy: mean of (volatility-weighted mean, harmonic mean)."""
    if not accs:
        return None
    wsum = sum(weights)
    weighted = sum(a * w for a, w in zip(accs, weights)) / wsum if wsum else 0.0
    harmonic = len(accs) / sum(1 / max(a, 1e-9) for a in accs)
    return (weighted + harmonic) / 2


def classify(drop):
    """Move label by win% drop: blunder ≥ 30, mistake ≥ 20, inaccuracy ≥ 10."""
    if drop >= 30:
        return "blunders"
    if drop >= 20:
        return "mistakes"
    if drop >= 10:
        return "inaccuracies"
    return None


def accuracy_block(plies, n_plies):
    """The sidecar `accuracy` block from the per-ply series (user moves only).

    `plies` entries need: user, phase, winBefore, winAfter, cpBefore/cpAfter
    (clamped)."""
    win_seq = [plies[0]["winBefore"]] + [p["winAfter"] for p in plies]
    weights = volatility_weights(win_seq, n_plies)

    def tally(subset):
        accs, ws, losses = [], [], []
        quality = {"inaccuracies": 0, "mistakes": 0, "blunders": 0}
        for p in subset:
            accs.append(move_accuracy(p["winBefore"], p["winAfter"]))
            ws.append(weights[p["ply"]])
            losses.append(max(0, min(1000, p["cpBefore"] - p["cpAfter"])))
            label = classify(p["winBefore"] - p["winAfter"])
            if label:
                quality[label] += 1
        game_acc = aggregate_accuracy(accs, ws)
        return {
            "accuracy": round(game_acc, 1) if game_acc is not None else None,
            "acpl": round(sum(losses) / len(losses)) if losses else None,
            "quality": quality,
        }

    user = [p for p in plies if p["user"]]
    total = tally(user)
    block = {
        "game": total["accuracy"],
        "acpl": total["acpl"],
        "quality": total["quality"],
        "method": "mean of volatility-weighted mean and harmonic mean of "
                  "per-move accuracies (Lichess formulas)",
        "phases": {},
    }
    for phase in ("opening", "middlegame", "endgame"):
        sub = [p for p in user if p["phase"] == phase]
        if not sub:
            continue
        t = tally(sub)
        block["phases"][phase] = {
            "accuracy": t["accuracy"],
            "acpl": t["acpl"],
            "quality": t["quality"],
            "plies": sum(1 for p in plies if p["phase"] == phase),
            "userMoves": len(sub),
        }
    return block


# --------------------------------------------------------------------------
# Step 2b Elo fit — pure function over per-ply Maia probabilities.
# --------------------------------------------------------------------------

def fit_positions(plies, relaxable=True):
    """Fit-eligible plies: user to move, more than one legal move, and
    |evalBefore| ≤ 6 pawns (clamped scale) — the eval cut is relaxed when it
    would leave the fit with no sample at all."""
    base = [p for p in plies if p["user"] and p.get("maia") and p["legalCount"] > 1]
    cut = [p for p in base if abs(p["cpBefore"]) <= ELO_EVAL_CUT * 100]
    if cut or not relaxable:
        return cut
    return base


def elo_fit(eligible):
    """Mean log-probability per band (floored at 0.1%), plus the honest
    display flags: flat = spread < 0.15 nats/move, floor = best band 1100."""
    if not eligible:
        return None
    by_band = {}
    for band in BANDS:
        logs = [math.log(max(p["maia"][str(band)]["played"], LOGPROB_FLOOR))
                for p in eligible]
        by_band[str(band)] = sum(logs) / len(logs)
    best = max(BANDS, key=lambda b: by_band[str(b)])
    spread = max(by_band.values()) - min(by_band.values())
    return {
        "best": best,
        "flat": spread < FLAT_SPREAD,
        "floor": best == 1100,
        "spread": round(spread, 3),
        "positions": len(eligible),
        "logProbByBand": {b: round(v, 3) for b, v in by_band.items()},
    }


def elo_display(fit):
    """The step-2b honest display rule: flat → unclear, floor → ≤1100."""
    if fit is None:
        return None
    if fit["flat"]:
        return "unclear"
    if fit["floor"]:
        return "≤1100"
    return f"≈{fit['best']}"


def acpl_ballpark(acpl):
    for limit, label in ACPL_BANDS:
        if limit is None or acpl <= limit:
            return label


# --------------------------------------------------------------------------
# Engine pass helpers.
# --------------------------------------------------------------------------

class Evaluator:
    """Depth-cached Stockfish evals, one `analyse` per unique (FEN, depth)."""

    def __init__(self, engine, user_color):
        self.engine = engine
        self.user = user_color
        self.cache = {}
        self.count = 0

    def eval_board(self, board, depth):
        """→ dict with score (PovScore from user POV), cp (clamped), raw
        pawns/mate for the sidecar, win%, and bestUci (None if terminal)."""
        key = (board.fen(), depth)
        if key in self.cache:
            return self.cache[key]
        if board.is_game_over():
            if board.is_checkmate():
                winner = "user" if board.turn != self.user else "opponent"
                cp = CLAMP_CP if winner == "user" else -CLAMP_CP
                out = {"eval": {"mate": 0, "winner": winner}, "cp": cp,
                       "win": win_pct(cp), "bestUci": None}
            else:
                out = {"eval": 0.0, "cp": 0, "win": win_pct(0), "bestUci": None}
        else:
            info = self.engine.analyse(board, chess.engine.Limit(depth=depth))
            pov = info["score"].pov(self.user)
            cp = max(-CLAMP_CP, min(CLAMP_CP, pov.score(mate_score=MATE_SCORE)))
            ev = {"mate": pov.mate()} if pov.is_mate() else round(pov.score() / 100, 2)
            best = info["pv"][0].uci() if info.get("pv") else None
            out = {"eval": ev, "cp": cp, "win": win_pct(cp), "bestUci": best}
        self.cache[key] = out
        self.count += 1
        return out


def is_mate_against(ev):
    return isinstance(ev, dict) and (
        (ev.get("mate", 0) < 0) or (ev.get("mate") == 0 and ev.get("winner") == "opponent"))


def is_mate_for(ev):
    return isinstance(ev, dict) and (
        (ev.get("mate", 0) > 0) or (ev.get("mate") == 0 and ev.get("winner") == "user"))


def phase_for(board, ply, endgame_started):
    """Phase rule: opening = plies 0–19; endgame from the first position with
    no queens or ≤ 6 non-pawn/non-king pieces total (sticky); middlegame
    between."""
    if not endgame_started:
        pieces = 0
        queens = 0
        for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
            n = len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK))
            pieces += n
            if pt == chess.QUEEN:
                queens = n
        endgame_started = queens == 0 or pieces <= 6
    if endgame_started:
        return "endgame", True
    return ("opening" if ply < 20 else "middlegame"), False


# --------------------------------------------------------------------------
# Maia harness driver (setup, server, one batch query).
# --------------------------------------------------------------------------

def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_maia_ready(port):
    maia_dir = ROOT / "tools" / "maia"
    weights_ok = all((maia_dir / "weights" / f"maia-{b}.pb").exists() for b in BANDS)
    engine_ok = (maia_dir / "vendor" / "package" / "dist" / "zerofishEngine.js").exists()
    if not (weights_ok and engine_ok):
        r = subprocess.run([str(maia_dir / "setup.sh")], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"maia setup.sh failed: {r.stderr.strip()[-400:]}")
    if not port_open(port):
        subprocess.Popen(
            ["node", str(maia_dir / "serve.mjs"), str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        for _ in range(50):
            if port_open(port):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("maia serve.mjs did not come up")


def maia_query(fens, port):
    """One batch call to tools/maia/query.cjs → {band: {fen: {moves, value}}}."""
    env = dict(os.environ, MAIA_PORT=str(port))
    env.setdefault("NODE_PATH", NODE_PATH)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"bands": BANDS, "positions": fens}, f)
        job = f.name
    try:
        r = subprocess.run(
            ["node", str(ROOT / "tools" / "maia" / "query.cjs"), job],
            capture_output=True, text=True, env=env, timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(f"query.cjs failed: {r.stderr.strip()[-400:]}")
        raw = json.loads(r.stdout)
    finally:
        os.unlink(job)
    return {band: {e["fen"]: e for e in entries} for band, entries in raw.items()}


# --------------------------------------------------------------------------
# Display helpers (house conventions: U+2212 minus, mates as #n / #−n).
# --------------------------------------------------------------------------

def disp_eval(ev):
    if isinstance(ev, dict):
        n = ev.get("mate", 0)
        return f"#{n}".replace("-", MINUS)
    return f"{ev:.2f}".replace("-", MINUS)


def disp_signed(x):
    return f"{x:+.2f}".replace("+", "").replace("-", MINUS)


def disp_pct(frac):
    pct = round(frac * 100)
    return f"{pct}%" if pct >= 1 else "<1%"


def arrow(uci):
    return [uci[0:2], uci[2:4]]


# --------------------------------------------------------------------------
# Main pipeline.
# --------------------------------------------------------------------------

def parse_pgn(path):
    with open(path, encoding="utf-8") as f:
        game = chess.pgn.read_game(f)
    if game is None:
        sys.exit(f"could not parse a game from {path}")
    headers = game.headers
    moves = list(game.mainline_moves())
    if not moves:
        sys.exit(f"no moves in {path}")
    return headers, moves


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pgn", help="path to the saved PGN (pgn/<stamp>.txt)")
    ap.add_argument("--color", required=True, choices=["white", "black"],
                    help="which side the user played")
    ap.add_argument("--depth", type=int, default=DEPTH_MAIN,
                    help="main Stockfish depth (default 20 per CLAUDE.md)")
    ap.add_argument("--no-maia", action="store_true",
                    help="skip the Maia pass (Stockfish-only page)")
    ap.add_argument("--maia-port", type=int,
                    default=int(os.environ.get("MAIA_PORT", 8123)))
    ap.add_argument("--sidecar", metavar="PATH",
                    help="sidecar draft path (default analysis/<stamp>.json)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing sidecar file")
    args = ap.parse_args()

    user_color = chess.WHITE if args.color == "white" else chess.BLACK
    headers, moves = parse_pgn(args.pgn)
    stamp = Path(args.pgn).stem
    sidecar_path = Path(args.sidecar) if args.sidecar else ROOT / "analysis" / f"{stamp}.json"
    if sidecar_path.exists() and not args.force:
        sys.exit(f"{sidecar_path} already exists — pass --force to overwrite")

    # ---- Stockfish pass (step 2) -----------------------------------------
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH)
    engine.configure({"Threads": 3, "Hash": 512})
    ev = Evaluator(engine, user_color)

    board = chess.Board()
    plies = []
    endgame = False
    pos_evals = []               # eval dict at every position 0..N
    for i, move in enumerate(moves):
        phase, endgame = phase_for(board, i, endgame)
        entry = {
            "ply": i,
            "san": board.san(move),
            "uci": move.uci(),
            "user": board.turn == user_color,
            "phase": phase,
            "fenBefore": board.fen(),
            "legalCount": board.legal_moves.count(),
        }
        pos_evals.append(ev.eval_board(board, args.depth))
        if entry["user"]:
            best = pos_evals[-1]["bestUci"]
            b2 = board.copy(stack=False)
            b2.push(chess.Move.from_uci(best))
            entry["bestEval"] = ev.eval_board(b2, args.depth)
            entry["bestSan"] = board.san(chess.Move.from_uci(best))
        board.push(move)
        plies.append(entry)
    pos_evals.append(ev.eval_board(board, args.depth))
    final_placement = board.board_fen()

    for i, p in enumerate(plies):
        before, after = pos_evals[i], pos_evals[i + 1]
        p.update(evalBefore=before["eval"], evalAfter=after["eval"],
                 winBefore=round(before["win"], 1), winAfter=round(after["win"], 1),
                 cpBefore=before["cp"], cpAfter=after["cp"],
                 bestUci=before["bestUci"])
        if p["user"]:
            p["cpBest"] = p["bestEval"]["cp"]
            p["evalBest"] = p["bestEval"]["eval"]
            p["swing"] = round((p["cpAfter"] - p["cpBefore"]) / 100, 2)
    log(f"stockfish pass done ({ev.count} evals, {len(plies)} plies)")

    # ---- Candidate mistakes (selection inputs, before Maia so the after-
    #      positions can ride the same batch query) --------------------------
    user_plies = [p for p in plies if p["user"]]
    for p in user_plies:
        p["cpLoss"] = max(0, min(1000, p["cpBefore"] - p["cpAfter"]))
        p["winDrop"] = round(p["winBefore"] - p["winAfter"], 1)
        p["allowsMate"] = (is_mate_against(p["evalAfter"])
                           and not is_mate_against(p["evalBefore"]))
        p["missedMate"] = (is_mate_for(p["evalBefore"])
                           and not is_mate_for(p["evalAfter"]))
    candidates = [p for p in user_plies
                  if p["allowsMate"] or p["missedMate"]
                  or p["winDrop"] >= 10 or p["cpLoss"] >= 100]
    candidates.sort(key=lambda p: (not p["allowsMate"], -p["cpLoss"]))
    candidates = candidates[:CANDIDATE_CAP]

    # ---- Maia pass (step 2b) ---------------------------------------------
    maia = None
    maia_error = None
    if not args.no_maia:
        try:
            ensure_maia_ready(args.maia_port)
            fens = []
            for p in user_plies:
                fens.append(p["fenBefore"])
            for p in candidates:      # after-played / after-best for E-points
                b = chess.Board(p["fenBefore"])
                b.push(chess.Move.from_uci(p["uci"]))
                p["fenAfterPlayed"] = b.fen()
                b = chess.Board(p["fenBefore"])
                b.push(chess.Move.from_uci(p["bestUci"]))
                p["fenAfterBest"] = b.fen()
                for fen in (p["fenAfterPlayed"], p["fenAfterBest"]):
                    if not chess.Board(fen).is_game_over():
                        fens.append(fen)
            fens = list(dict.fromkeys(fens))
            maia = maia_query(fens, args.maia_port)
            log(f"maia query done ({len(BANDS)} bands x {len(fens)} positions)")
        except Exception as e:
            maia_error = str(e)
            maia = None
            log(f"maia pass FAILED, falling back to Stockfish-only: {maia_error}")

    if maia:
        for p in user_plies:
            p["maia"] = {}
            for band in BANDS:
                r = maia[str(band)][p["fenBefore"]]
                p["maia"][str(band)] = {
                    "played": round(r["moves"].get(p["uci"], 0.0) / 100, 4),
                    "best": round(r["moves"].get(p["bestUci"], 0.0) / 100, 4),
                    "value": round(r["value"], 3),
                }

    # ---- Elo fit + human-findable scan (step 2b) -------------------------
    fit = phase_fits = None
    if maia:
        fit = elo_fit(fit_positions(plies))
        phase_fits = {}
        for phase in ("opening", "middlegame", "endgame"):
            sub = [p for p in plies if p["phase"] == phase]
            f = elo_fit(fit_positions(sub))
            if f:
                phase_fits[phase] = f
        band = str(fit["best"])
        rechecks = 0
        for p in user_plies:
            moves_at_band = maia[band][p["fenBefore"]]["moves"]
            human = p["bestUci"]
            for uci, prob in sorted(moves_at_band.items(), key=lambda kv: -kv[1]):
                if prob < HUMAN_MIN_PROB:
                    break
                if uci == p["bestUci"]:
                    human = uci
                    break
                b = chess.Board(p["fenBefore"])
                b.push(chess.Move.from_uci(uci))
                cand = ev.eval_board(b, DEPTH_RECHECK)
                rechecks += 1
                if cand["cp"] >= p["cpBest"] - HUMAN_WINDOW_CP:
                    human = uci
                    break
            p["humanBestUci"] = human
            p["humanBestSan"] = chess.Board(p["fenBefore"]).san(chess.Move.from_uci(human))
        log(f"human-findable scan done ({rechecks} depth-{DEPTH_RECHECK} re-checks)")

    # ---- Per-candidate Maia numbers + weighting --------------------------
    def expected_score(fen):
        b = chess.Board(fen)
        if b.is_game_over():
            if b.is_checkmate():
                return 1.0 if b.turn != user_color else 0.0
            return 0.5
        v = maia[band][fen]["value"]        # side to move = opponent
        return 1 - v if b.turn != user_color else v

    for p in candidates:
        if maia:
            r = maia[band][p["fenBefore"]]
            p["playedPopularity"] = r["moves"].get(p["uci"], 0.0) / 100
            p["bestFindability"] = r["moves"].get(p["bestUci"], 0.0) / 100
            p["humanBestFindability"] = r["moves"].get(p["humanBestUci"], 0.0) / 100
            p["expectedPointsLost"] = round(
                expected_score(p["fenAfterPlayed"]) - expected_score(p["fenAfterBest"]), 2)
            pop = p["playedPopularity"]
            p["recurrenceRisk"] = ("high" if pop >= 0.25 else
                                   "medium" if pop >= 0.10 else "low")
            p["weight"] = round(p["cpLoss"] * max(pop, 0.05), 1)
        else:
            p["weight"] = p["cpLoss"]
    candidates.sort(key=lambda p: (not p["allowsMate"], -p["weight"]))

    # ---- Retry probes (step 2d) — reuse build-drills.compute_retry -------
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_drills", ROOT / "tools" / "build-drills.py")
    build_drills = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_drills)
    for p in candidates:
        mk = {"fenBefore": p["fenBefore"], "playedUci": p["uci"],
              "bestUci": p["bestUci"]}
        if maia:
            mk["humanBestUci"] = p["humanBestUci"]
        p["retry"] = build_drills.compute_retry(mk, engine)
    engine.quit()
    log(f"retry probes done ({len(candidates)} candidates)")

    # ---- Accuracy block (step 2c) ----------------------------------------
    acc = accuracy_block(plies, len(plies))

    # ---- Sidecar draft (step 4b, minus the hand-written mistakes) --------
    game_date = headers.get("Date", "").replace(".", "-")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", game_date):
        game_date = date.today().isoformat()
    opening = headers.get("Opening") or headers.get("ECO") or ""
    engine_block = {
        "stockfish": f"depth {args.depth}",
        "generated": date.today().isoformat(),
    }
    if maia:
        engine_block["maia"] = ("Maia-1 rating-band networks 1100-1900 via "
                                "zerofish WASM lc0, nodes=1")

    def sidecar_ply(p):
        out = {"ply": p["ply"], "san": p["san"], "uci": p["uci"],
               "user": p["user"], "phase": p["phase"], "fenBefore": p["fenBefore"],
               "evalBefore": p["evalBefore"], "evalAfter": p["evalAfter"],
               "winBefore": p["winBefore"], "winAfter": p["winAfter"],
               "bestUci": p["bestUci"]}
        if p["user"]:
            out["evalBest"] = p["evalBest"]
            out["swing"] = p["swing"]
            if p.get("maia"):
                out["maia"] = p["maia"]
            if p.get("humanBestUci"):
                out["humanBestUci"] = p["humanBestUci"]
        return out

    sidecar = {
        "schema": 1,
        "game": {
            "white": headers.get("White", "?"), "black": headers.get("Black", "?"),
            "result": headers.get("Result", "*"), "date": game_date,
            "event": headers.get("Event", ""), "opening": opening,
            "userColor": args.color,
            "pgnFile": f"pgn/{stamp}.txt", "pageFile": f"games/{stamp}.html",
        },
        "engine": engine_block,
        "plies": [sidecar_ply(p) for p in plies],
        "accuracy": acc,
        "eloFit": fit,
        "mistakes": [],
    }
    sidecar_path.parent.mkdir(exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar, indent=1, ensure_ascii=False))

    # ---- One JSON document to stdout -------------------------------------
    display = {
        "accuracy": f"{round(acc['game'])}%" if acc["game"] is not None else None,
        "acpl": acc["acpl"],
        "moveQuality": acc["quality"],
        "phaseAccuracy": {ph: f"{round(b['accuracy'])}%"
                          for ph, b in acc["phases"].items()
                          if b["accuracy"] is not None},
    }
    if fit:
        display["estimatedElo"] = elo_display(fit)
        note = {"unclear": f"band fit unclear (flat, spread {fit['spread']})",
                "≤1100": "band fit ≤1100 (floor)"}.get(
                    display["estimatedElo"], f"band fit {display['estimatedElo']}")
        display["estimatedEloNote"] = (
            f"{note}; ACPL {acc['acpl']} is typical of "
            f"{acpl_ballpark(acc['acpl'])} rapid")
        display["phaseElo"] = {
            ph: f"{elo_display(f)} · {f['positions']} moves"
            for ph, f in phase_fits.items()}
        weakest = min(
            (ph for ph in acc["phases"] if acc["phases"][ph]["accuracy"] is not None),
            key=lambda ph: acc["phases"][ph]["accuracy"], default=None)
        display["weakestPhase"] = weakest

    def move_note(p):
        note = {"ply": p["ply"], "best": p["bestSan"], "bestArrow": arrow(p["bestUci"])}
        if maia:
            note["humanBest"] = p["humanBestSan"]
            note["humanBestArrow"] = arrow(p["humanBestUci"])
        return note

    def candidate_out(rank, p):
        game_mk = {
            "ply": p["ply"], "played": p["san"], "best": p["bestSan"],
            "evalBefore": disp_eval(p["evalBefore"]),
            "evalAfter": disp_eval(p["evalAfter"]),
            "evalBest": disp_eval(p["evalBest"]),
            "swing": "mate" if p["allowsMate"] else disp_signed(p["swing"]),
            "playedArrow": arrow(p["uci"]), "bestArrow": arrow(p["bestUci"]),
            "winBefore": f"{round(p['winBefore'])}%",
            "winAfter": f"{round(p['winAfter'])}%",
        }
        if maia:
            game_mk.update({
                "playedPopularity": disp_pct(p["playedPopularity"]),
                "bestFindability": disp_pct(p["bestFindability"]),
                "humanBest": p["humanBestSan"],
                "humanBestArrow": arrow(p["humanBestUci"]),
                "humanBestFindability": disp_pct(p["humanBestFindability"]),
                "recurrenceRisk": p["recurrenceRisk"],
            })
            if abs(p["expectedPointsLost"]) >= 0.005:
                game_mk["expectedPointsLost"] = disp_signed(p["expectedPointsLost"])
        game_mk["retry"] = p["retry"]
        side = {"fenBefore": p["fenBefore"], "playedUci": p["uci"],
                "bestUci": p["bestUci"],
                "winBefore": p["winBefore"], "winAfter": p["winAfter"]}
        if maia:
            side["humanBestUci"] = p["humanBestUci"]
        return {"rank": rank, "ply": p["ply"], "cpLoss": p["cpLoss"],
                "winDrop": p["winDrop"], "weight": p["weight"],
                "allowsMate": p["allowsMate"], "missedMate": p["missedMate"],
                "game": game_mk, "sidecar": side}

    def user_ply_summary(p):
        out = {"ply": p["ply"], "san": p["san"], "phase": p["phase"],
               "best": p["bestSan"],
               "evalBefore": p["evalBefore"], "evalAfter": p["evalAfter"],
               "swing": p["swing"],
               "winBefore": p["winBefore"], "winAfter": p["winAfter"]}
        if p.get("maia"):
            out["playedPopularity"] = p["maia"][band]["played"]
            out["humanBest"] = p["humanBestSan"]
        return out

    doc = {
        "game": dict(sidecar["game"], stamp=stamp),
        "engine": engine_block,
        "counts": {"plies": len(plies), "userMoves": len(user_plies),
                   "finalPlacement": final_placement},
        "accuracy": acc,
        "eloFit": fit,
        "phaseEloFits": phase_fits,
        "display": display,
        "evals": [p["winAfter"] for p in plies],
        "moveNotes": [move_note(p) for p in user_plies],
        "mistakeCandidates": [candidate_out(i + 1, p)
                              for i, p in enumerate(candidates)],
        "userPlies": [user_ply_summary(p) for p in user_plies],
        "sidecarDraft": str(sidecar_path.relative_to(ROOT)
                            if sidecar_path.is_relative_to(ROOT) else sidecar_path),
    }
    if maia_error:
        doc["maiaError"] = maia_error
    print(json.dumps(doc, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
