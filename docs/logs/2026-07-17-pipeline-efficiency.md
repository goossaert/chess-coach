# Implementation log — pipeline efficiency

**Date**: 2026-07-17 ·
**Plan**: `docs/0008-plan-pipeline-efficiency.md` ·
**Branch**: `main` (per the session's explicit instruction — no feature
branch) ·
**Commits**: new tools + quieting (one commit), CLAUDE.md step references +
this log (one commit)

## What was implemented

1. **`tools/analyze-game.py`** — steps 2/2b/2c/2d as one call. One
   invocation runs the depth-20 Stockfish pass (FEN-cached, one `analyse`
   per unique position), builds the Maia job and shells out **once** to
   `tools/maia/query.cjs` (auto-running `setup.sh` and starting `serve.mjs`
   first when needed), computes win%/accuracy/ACPL/move-quality and the
   honest Elo fit (game + per phase) from the same in-memory per-ply data,
   ranks mistake candidates (mates first, then swing × recurrence with the
   5% popularity floor), runs the depth-18 human-findable scan and the
   multipv-5 depth-18 retry probes (via `build-drills.compute_retry`, so
   the two can never drift), and prints **one JSON document**: GAME-ready
   `display` values, `moveNotes`, `evals`, ranked `mistakeCandidates`
   (display fields + numeric sidecar fields + `retry`), the
   `accuracy`/`eloFit` blocks, and a compact `userPlies` summary. It also
   writes the step-4b sidecar draft (everything except `mistakes`) straight
   to `analysis/<stamp>.json`. On any Maia failure it degrades to a
   Stockfish-only run with `maiaError` set (`--no-maia` forces this);
   an existing sidecar is never overwritten without `--force`. stderr is
   ≤ 5 phase lines.

2. **`tools/verify-game.py` (+ `tools/verify-game.cjs`)** — the whole
   step-6 checklist as one call. The `.cjs` half loads the page **once**
   headless and runs every in-page assertion in a single `evaluate`
   (error/banner, total, placement, every mistake-card click, arrows +
   legend + side-by-side on every position, Maia/v3 field-presence iff
   rules, the full eval-graph battery, the full retry battery incl.
   illegal/wrong/solution/acceptable/navigate-away paths, page errors);
   the `.py` half replays the PGN with python-chess and runs all data
   checks (movesSan↔PGN parity, move/arrow legality, humanBest depth-18
   eval re-checks, tag vocabulary, drill-link provenance, retry-object
   soundness, and the sidecar cross-checks: replay, win%/swing formulas,
   evals↔winAfter, mistakes parity, honest-Elo display rule, Maia
   probability sanity). Output: `all checks passed (N checks)` on a healthy
   page; otherwise one line per failure naming the check and ply. Hooks or
   fields a page predates are skipped, not failed. `--page-only` verifies
   template demos; `--no-engine` skips only the Stockfish probes.

3. **Noise audit (plan item 3)** — `tools/maia/setup.sh` no longer leaks
   `npm notice` chatter or patch messages on the happy path (errors stay
   verbose; success prints only `maia setup complete`).
   `tools/build-drills.py` and `tools/build-progress.py` already print
   exactly one line each and nothing per sidecar — confirmed, unchanged.
   `serve.mjs` prints one startup line — left as is. `query.cjs`'s
   per-band stderr lines are captured by `analyze-game.py` and summarized
   to one line. A root `.gitignore` for `__pycache__/` was added
   (`analyze-game.py` imports `build-drills.py` at runtime, which writes
   bytecode there).

4. **`CLAUDE.md`** — steps 2 and 6 now open with the one-call commands;
   step 2b's harness snippet notes the script runs it itself; step 4b
   explains the draft-then-edit-mistakes flow; the two tools are in the
   repo layout; an intro paragraph records that this changed tooling, not
   analysis. The full formulas/checklists remain inline as the normative
   spec.

## Verification results

- **Exact math reproduction (offline)** — every math function was run over
  the *recorded* per-ply data of all nine existing sidecars and diffed
  against their stored blocks: phases, win%, swing, quality tallies, game
  accuracy, per-phase accuracy, ACPL, and the Elo fit
  (best/flat/floor/positions for all nine; spread and per-band log-probs
  within ±0.002, the rounding of the stored 4-dp probabilities). 100%
  match. Two implementation details of the part-1 pipeline had to be
  pinned down to get there, both now encoded in `analyze-game.py`:
  - **ACPL loss = clamped(evalBefore) − clamped(evalAfter)** (not
    vs. evalBest) — the only variant matching all nine sidecars (9/9), and
    also lila's definition.
  - **Volatility weights**: population stdev of the win% window *ending at
    the position after each move*, truncated at the start — the only
    alignment matching all 33 stored accuracy values (game + phases ×
    nine games). CLAUDE.md's loose "sliding window" description is
    unchanged — it explicitly allows the approximation; the script
    reproduces the established implementation so numbers stay comparable
    across the repo.
- **Live end-to-end** (`pgn/2026-07-09-12-11…`, depth 18 to match the
  backfill): 62 plies, one call, exit 0. Versus the committed sidecar:
  Maia probabilities **byte-identical** (max |Δ| = 0.0 — deterministic at
  nodes=1), quality tally identical, accuracy 66.9 vs 67.3, ACPL 152 vs
  148, evals mean |Δ| 13 cp — pure Threads-3 engine nondeterminism (any
  two runs of the old flow differ the same way; the offline test above is
  the formula-identity proof). Elo fit landed one band over (1400 vs 1300,
  23 vs 24 fit positions): one position's |eval| sat on the 6-pawn
  exclusion boundary under re-evaluated evals. All five committed mistakes
  appear among the 14 ranked candidates, with identical retry
  solutions/legal lists. Stockfish-only mode smoke-tested separately
  (every Maia field absent, sidecar draft valid).
- **Three-page verify matrix** (per the plan):
  `games/2026-07-14…` (pre-arrows, no moveNotes/Maia fields) — 87 checks,
  all pass, feature checks skipped rather than failed;
  `games/2026-07-09-12-11…` (Maia + arrows, no retry/evals) — 103 checks,
  all pass, including the depth-18 humanBest re-check probes;
  `template.html --page-only` (all fields: retry, evals, practice-first)
  — 66 checks, all pass. `games/2026-07-15…` reports exactly its two
  **known, documented** pre-existing violations (`±0.00`
  expectedPointsLost; `estimatedElo: "≈1900"` vs its flat fit — the
  part-3 log's designated backfill target) and nothing else; a manual
  walk of today's checklist reaches the same verdict, which is the
  agreement the plan asks for.
- **Fault injection**: corrupting one `moveNotes` `bestArrow` on the
  2026-07-15 page → `FAIL moveNotes moves legal, arrows match: ply 2
  bestArrow mismatch`; an off-by-one `fenBefore` at sidecar ply 10 →
  `FAIL sidecar plies replay legally…: ply 10: fenBefore mismatch`. Both
  named precisely; both files restored from git afterwards.
- **Round trips / output volume** (62-ply game, the plan's requested
  evidence):
  - *Analysis, old*: ≈ 10–15 Bash calls per game (per-pass scripts for
    Stockfish loop, maia job build, query, fit, human-findable scan,
    accuracy, retry probes), with the intermediate per-ply tables and the
    raw Maia output (~0.5 MB of per-band move maps for a game this size)
    flowing back through tool results at least once, and the full ~46 KB
    sidecar typed back out by the model.
  - *Analysis, new*: **1 call**, 4 stderr lines + **38 KB** stdout; the
    46 KB per-ply sidecar draft goes straight to disk and never enters
    context.
  - *Verification, old*: ≈ 6–10 calls (several Playwright evaluates +
    several python-chess scripts), each printing its own output.
  - *Verification, new*: **1 call**, **one line** on a healthy page
    (103 checks inside).
- `build-drills.py` / `build-progress.py` re-run after all changes:
  outputs byte-identical (no git diff), one line each.

## Judgment calls / deviations from the plan

- **stdout carries the per-ply series in compact form** (`userPlies`, one
  entry per user move) while the full-fidelity plies (with the 9-band
  Maia tables) go into the sidecar draft the script writes at the same
  time. The plan's letter says stdout holds "the per-ply series"; its goal
  is cutting the volume flowing into context, and pushing ~46 KB of
  per-band tables through stdout so the model can re-type them into the
  sidecar would defeat exactly that. Everything the model *reads* is on
  stdout; everything the sidecar *stores* is already in the draft file.
- **Retry probes run for every ranked candidate** (cap 20), not only 3–6
  "selected" ones — selection is the model's step-3 judgment, which
  hasn't happened yet at analysis time. Probes cost seconds; this keeps
  the model free to pick any candidate and still have `retry` ready.
- **`verify-game` is a `.py` + `.cjs` pair, one command.** The plan
  offered `.py` or `.mjs`; python-chess only exists in the venv and
  Playwright only in the Node tree (and ESM ignores `NODE_PATH`, hence
  `.cjs`, like the Maia harness). The `.py` entry point spawns the `.cjs`
  as its single subprocess.
- **Engine-noise slack in the humanBest re-check** (0.5-pawn window +
  0.15 slack): re-running Stockfish never reproduces the original evals
  exactly, so the verifier only flags a humanBest that misses the window
  by more than typical depth-18 jitter — otherwise every historical Maia
  page would false-fail on probe noise.
- **`analyze-game.py` bootstraps the Maia harness itself** (setup.sh +
  serve.mjs when missing/down) — two more round trips the session no
  longer spends; the manual commands still work and stay documented.

## Other notes for later parts

- The Elo-fit eval-cut boundary (|eval| > 6) is sensitive to engine noise
  for positions sitting near ±6.00: two runs can differ by one fit
  position and occasionally one band. The flat/floor display rule is
  unaffected (flags recompute from whatever run produced the sidecar);
  worth remembering when part 4 backfills old pages and numbers shift by
  a band.
- `tools/analyze-game.py --depth` exists for matching the depth-18
  backfill sidecars in comparisons; per-game production runs should stay
  at the default depth 20 per CLAUDE.md.
- Long games at depth 20 can run several minutes — start the call in the
  background if the session's tool timeout is a concern; stderr's four
  phase lines double as a progress indicator.
