# Implementation log — learning loop part 1: foundation

**Date**: 2026-07-17 ·
**Plan**: `docs/0005-plan-learning-loop-1-foundation.md` ·
**Branch**: `claude/learning-loop-1-foundation-9f7h8v` ·
**Commits**: template + drill links + CLAUDE.md (one commit each), sidecar
backfill (one commit, 9 files, ~35k lines)

## What was implemented

1. **`tools/drill-links.json`** — mistake-taxonomy → Lichess practice-link
   map. All 14 vocabulary tags have 2–3 links each; every URL was checked to
   appear verbatim in
   `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.md`
   (lichess.org itself is unreachable from the sandbox). `time-trouble`
   (reserved tag) maps to Puzzle Storm / Puzzle Streak.

2. **`template.html`** — five additions, all rendered only when their GAME
   fields are present (older pages render unchanged):
   - `#head-stats` stat strip: `accuracy`, `acpl`, `moveQuality`
     (?! / ? / ?? tally) as chips under the strength line;
   - phase accuracy (`phaseAccuracy`) merged into the existing phase chips
     via a shared `buildPhaseRow()`; when there is no Maia strength line the
     phase chips render inside the stat strip instead;
   - `.tag-chip` chips on mistake cards (`tags`), next to the recur-tag;
   - `.win-row` in the feedback panel ("your winning chances: 92% → 45%",
     from `winBefore`/`winAfter`), placed right under the eval compare grid;
   - `.drill-links` list ("Where to practice", from `drillLinks`) at the
     bottom of the takeaways box; the box now renders if takeaways *or*
     drill links exist.
   - The demo GAME data now carries every new field, so `template.html`
     itself doubles as the all-fields test page.

3. **`CLAUDE.md`** — bumped to Version 3. New step 2c (win% / per-move
   accuracy / game accuracy / ACPL / move classification formulas, per
   phase too), taxonomy + `drillLinks` in step 3, new step 4b with the full
   sidecar schema and the "commit pgn + html + json together" rule, the
   `expectedPointsLost` ±0.00 **omission** rule (replacing "±0.00 ok"),
   extended step-6 verification, `analysis/` and `tools/drill-links.json`
   in the repo layout.

4. **`analysis/*.json` backfill** — nine sidecars (`schema: 1`), one per
   `pgn/*.txt`, from a full pipeline re-run. No existing page, PGN, or
   index file was touched.

## Backfill pipeline parameters (for reproducibility)

- **Stockfish**: `/usr/games/stockfish`, depth 18 (plan allows 18–20 for
  backfill), Threads 3, Hash 512. Every position of every game evaluated
  once (1,127 unique FENs incl. after-best and humanBest-candidate
  positions); evals cached by full FEN during the run.
- **Maia**: Maia-1 rating-band networks 1100–1900 via the committed
  zerofish WASM harness (`tools/maia/`), `go nodes 1`, all 9 bands × all
  413 user-to-move positions.
- **Per-ply fields**: evals as numeric pawns (2 dp, user POV); mates as
  `{"mate": n}`; a game-over-by-mate position is
  `{"mate": 0, "winner": "user"|"opponent"}` (JSON cannot sign a zero).
  `swing` and win% are computed on the ±1000 cp clamped scale
  (mate scores mapped through `mate_score=100000` first).
- **Phases**: opening = plies 0–19; endgame from the first position with
  no queens on the board *or* ≤ 6 non-pawn/non-king pieces total (once
  endgame starts it never reverts); middlegame between.
- **Game accuracy**: mean of (volatility-weighted mean, harmonic mean) of
  per-move accuracies — the lila aggregation, with the window
  `clamp(plies/10, 2, 8)` over the user-POV win% sequence and weights
  clamped to [0.5, 12]; recorded in each sidecar's `accuracy.method`.
- **Elo fit**: mean log-probability of the played moves per band, floored
  at 0.1%, only positions with > 1 legal move (413 → per-game 31–66).
  `flat` = (best − worst mean log-prob) < 0.15 — chosen because the one
  page with a stated opinion (emgosr, spread 0.138) calls its own fit
  "nearly flat", while clearly separated fits showed spreads ≥ 0.19.
- **humanBest**: at the fit band, scanning moves by descending
  probability, first move whose depth-18 eval stays within 0.5 pawns of
  the best move's eval; the engine's best always qualifies; candidates
  below 0.5% probability are skipped (nothing that rare is
  "human-findable" — falls back to best). Present on **every** user ply
  in every sidecar.
- **Mistake tags**: assigned by hand for all 41 existing page mistakes by
  reading each page's title/explanation (per the plan's backfill
  instruction), then written into the sidecars. Every tag is from the
  step-3 vocabulary; 13 of 14 tags occur at least once (`time-trouble`
  reserved — no clock data).
- **Sidecar mistakes** keep the page's values verbatim (ply/played/best,
  prose, Maia percentages) and add `tags`, `fenBefore`, `playedUci`,
  `bestUci`, `humanBestUci` (from the page's SANs), `winBefore`/`winAfter`
  (recomputed at depth 18).

## Verification results

All green at final state: **266 data/math checks + 89 Playwright checks.**

- **Template compatibility** (Playwright, headless Chromium):
  `games/2026-07-14-17-37-maia-600-vs-guest.html` (pre-v2),
  `games/2026-07-15-21-31-emgosr-vs-maia-800.html` (v2 + arrows), and
  `template.html` (all new fields). On all three: `__review.error` null,
  error banner hidden, no page errors, `total()` matches the PGN ply
  count, `placement(total)` equals the python-chess final placement, every
  mistake-card click lands on its ply and activates the panel. New UI
  elements appear **iff** their fields are set (stat strip, win row, drill
  links, tag chips, recur-tag, typ-badge, find-row), arrows + legend show
  on user-move positions and not on opponent positions.
- **Math**: win%(cp 0) = 50, symmetric around 50 for ±cp, clamp ≈ 97.5% at
  ±1000; accuracy(drop 0) ≈ 100 (the Lichess formula's true maximum is
  99.9999), accuracy ∈ [0, 100] across the range; every sidecar's
  winBefore/After re-derivable from its evals through the formula.
- **Sidecars**: one per `pgn/*.txt` with matching stamps; every ply
  replays legally with python-chess and matches its recorded FEN and UCI;
  every sidecar mistake matches its page's GAME mistake (ply/played/best);
  all tags from the vocabulary (1–3 each); every user ply carries `maia`
  and `humanBestUci`; average Maia probability of the played moves at the
  fit band is 0.14–0.35 per game vs. a ~0.03 random baseline (no
  FEN/move misalignment).
- **Drill links**: every URL in `tools/drill-links.json` appears in the
  2026-07-13 report; every vocabulary tag has a mapping; template renders
  only file-sourced URLs in the demo.

## Deviation from the plan

The plan's math check "**blunder count ≥ count of mistakes with |swing| ≥
3.0** in each backfilled game" is mathematically incompatible with the
plan's own (Lichess) classification "blunder = win% drop ≥ 30 points",
and failed for 8 of 9 games as literally stated. The cause is eval
saturation in decided positions — the same phenomenon the plan itself
cites when replacing "±0.00" `expectedPointsLost` with win% framing:

- "missed #3" / "missed #1" mistakes: 97.5% → 97.5%, win% drop 0.0 — the
  user was completely winning either way;
- "mate"-swing mistakes in already-lost positions: e.g. 5.0% → 2.5%;
- big pawn swings from lopsided evals: e.g. −9.31 pawns but 10.5% → 2.5%.

Resolution: the Lichess win%-drop classification was kept as normative
(it is what the plan specifies for `moveQuality`), and the verification
tests the invariant that actually must hold — **every page mistake whose
win% drop is ≥ 30 points is tallied as a blunder** (passes 9/9). The 16
saturated big-swing mistakes are logged as informational, not failures.
Nothing in the shipped data was bent to force the literal check.

## Other notes for later parts

- Two smaller judgment calls during verification: the per-move accuracy
  formula's true maximum is 99.9999 (not 100.0 exactly — clamp is [0,100]
  but drop 0 gives 103.1668 − 3.1669), and "Maia probability well above
  random" was concretized as avg > 0.10 vs. the ~0.03 random baseline
  (the engine-vs-engine game 2026-07-11 sits lowest at 0.14, consistent
  with the CLAUDE.md caveat about off-beat engine play).
- Depth-18 backfill evals differ slightly from the pages' depth-20 evals;
  sidecar `plies[]` numbers are the depth-18 truth, sidecar `mistakes[]`
  keep the page's displayed strings. Fit bands agreed with the one page
  that reports one (emgosr: ≈1900, flat).
- Backfilled sidecars' `engine.generated` is
  `"2026-07-17 backfill (docs/0005 part 1)"` — a marker for telling
  backfilled sidecars from ones written at page-generation time.
- The backfill scripts were session-scratchpad tooling (not committed —
  the plan's deliverables list no pipeline script; the normal workflow is
  per-game, driven by CLAUDE.md). Everything needed to regenerate a
  sidecar is in CLAUDE.md steps 2–4b plus the parameters above.
- `games/index.html`, `pgn/`, and all existing `games/*.html` are
  byte-identical to before this part, per the plan's "sidecars only"
  backfill rule.
