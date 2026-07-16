# Learning Loop 3 of 4 — Insight: Eval Graph, Progress Dashboard & Honest Elo

**Series**: part 3 of the four-part *faster learning loop* series. Run the
parts sequentially, one fresh session each:

1. `docs/0005-plan-learning-loop-1-foundation.md` — sidecars, taxonomy, accuracy, drill links
2. `docs/0006-plan-learning-loop-2-practice.md` — retry mode + personal drill deck
3. `docs/0007-plan-learning-loop-3-insight.md` — **this plan**
4. `docs/0008-plan-learning-loop-4-polish.md` — highlights, opening report, trend regen, clocks, backfill

**Prerequisites — verify before starting**: parts 1 and 2 must be complete.
Check that `analysis/` holds one sidecar per `pgn/*.txt` game with per-ply
evals/win% and `accuracy`/`eloFit` blocks; that `drills/index.html` and
`tools/build-drills.*` exist; and that `CLAUDE.md` documents sidecars,
taxonomy, accuracy fields, and the drill-deck step. If part 1's sidecars are
missing, **stop and run 0005 first** (part 2 is a soft prerequisite — only
the drill-deck link placement in the index is shared).

## Goal

The user's stated goal for the series: *speed up learning from mistakes and
improve Elo.* This part supplies orientation and the feedback signal: see
each game's shape at a glance (Lichess's advantage graph), see whether the
training is actually moving the needle over time, and stop showing a
strength estimate that misleads.

## Context — repo essentials (self-contained)

`goossaert/chess-coach` turns PGN games into interactive coaching pages. The
workflow in `CLAUDE.md` runs a Stockfish pass (depth 20, `python-chess` +
`/usr/games/stockfish`, evals from the user's perspective) and a Maia
rating-band pass (`tools/maia/`, Maia-1 bands **1100–1900 only** via
zerofish WASM lc0 in headless Chromium — nothing below 1100; `pip install
maia3` and Maia-2/3 checkpoints are blocked by the sandbox proxy). Pages are
generated in `games/` from `template.html` (only the `const GAME = {…};`
block and `<title>` are replaced in generated files); sidecars in
`analysis/` persist per-ply evals, win%, Maia band probabilities, accuracy,
and the Elo fit. Cross-game material lives in `reports/`. Verification is
headless Playwright (`NODE_PATH=/opt/node22/lib/node_modules`, `.cjs`
scripts) against `window.__review` hooks.

**Design principles (non-negotiable):** new GAME fields are optional — the
template renders old pages unchanged; Stockfish is the only evaluator; UI
changes go in `template.html` or new standalone files, never in generated
pages; `games/index.html` edits stay inside marked regions; no external
JS/CDNs in pages; system `pip install chess` fails — use the venv recipe in
`CLAUDE.md`.

**Formulas already in use (from part 1)** — win% from centipawns:
`win% = 50 + 50 · (2 / (1 + exp(−0.00368208 · cp)) − 1)`, cp clamped to
±1000, mates mapped through a large `mate_score` first.

### Why this part exists (findings from the page review)

- No eval graph: the reader must click through cards to sense where the game
  swung; Lichess shows it in one glance.
- No progress tracking: nothing shows accuracy/Elo/blunder-rate over time,
  so the user cannot tell whether drilling a gap is closing it.
- The Elo estimate misleads exactly where the user plays: the 2026-07-15
  page displays `estimatedElo: "≈1900"` with a note admitting the fit is
  "nearly flat", while the user was losing to Maia 800 — the band floor is
  1100, the games are engine games (out of Maia's human-vs-human
  distribution), and a 35-move forced endgame dominated the phase fit
  (`endgame: ≈1100 · 35 moves`).

## Scope of this part

### 1. Eval graph under the board (Lichess advantage chart)

A clickable inline-SVG sparkline in `template.html`, rendered between the
board controls and the feedback panel (exact placement at implementer's
judgment, house style — dark panel, gold/rust accents):

- x = ply, y = **win%** from the user's perspective (never raw centipawns —
  win% is bounded, so mate scores don't explode the scale); 50% midline
  marked.
- Mistake plies flagged with rust dots; clicking a dot behaves exactly like
  clicking that mistake's card (jump + feedback + `mistake-active`).
- A cursor marks the current replay position; clicking anywhere on the graph
  jumps the replay to that ply; stepping the replay moves the cursor
  (two-way sync).
- Data: new optional top-level GAME field, one entry per half-move —

  ```js
  evals: [52.1, 48.7, …],   // win% after each ply, user's perspective
  ```

  written by the pipeline from the Stockfish pass (the sidecar already
  stores the underlying numbers). Renders only when present — old pages show
  no graph. Test hooks: `window.__review.graphPly()` /
  `graphClick(ply)` or equivalent, for Playwright.

Keep it dependency-free SVG like the board renderer. Update `CLAUDE.md`
(schema reference + generation step + verification).

### 2. Progress dashboard: `reports/progress.html`

Generated from the sidecars by a new `tools/build-progress.*` script
(same replace-a-marked-data-block discipline: commit a
`progress-template.html` or generate the whole file — implementer's choice,
but self-contained, inline-SVG charts, house style):

- Per-game series over time (x = the filename stamp's date):
  **accuracy**, **ACPL**, **blunders per game**, **estimatedElo** (with its
  confidence state from item 3 — flat/floor fits drawn hollow or annotated,
  not as confident points), and **per-phase accuracy**.
- A **tag recurrence table**: for each taxonomy tag, mistakes per game
  across the last N games (a small multiples row or count matrix) — this is
  the "is the gap shrinking after drilling it?" view, the feedback signal
  the whole series exists for.
- Every game name links to its `games/<stamp>.html` page.
- **Workflow step** (`CLAUDE.md`): after generating a page + sidecar (and
  the drill deck), re-run the progress builder and commit
  `reports/progress.html` along with them. Link the dashboard from the
  marked tools/region of `games/index.html` (region introduced in part 2;
  if absent, add it per part 2's spec).

### 3. Honest Elo estimation

Fix the misleading display rather than widen it. Changes to the Maia step in
`CLAUDE.md` (and to the fit code used during generation):

- **Mechanical display rule**: when the best-fit band rails at the floor
  (1100) or the fit is flat (log-prob spread between best and worst band
  below a documented threshold — pick one during implementation and write it
  into `CLAUDE.md`), display `estimatedElo: "≤1100"` or `"unclear"` — never
  a confident-looking middle number. The pipeline decides this, not
  editorial judgment. Record `flat`/`floor` flags in the sidecar `eloFit`.
- **Exclude low-information stretches** from the fit: forced/only-move
  positions (already excluded), plus positions where |eval| > ~6 pawns
  (dead-won/dead-lost conversion phases — the 35-move endgame case) unless a
  phase would otherwise have no sample.
- **Corroborating signal**: an accuracy/ACPL-based rating ballpark from
  published ACPL↔rating regressions, stated only in `estimatedEloNote` as
  approximate corroboration — e.g. "band fit ≤1100 (floor); ACPL 78 is
  typical of ~900–1100 rapid". Two weak signals agreeing beat one flat fit.
- Document (in `CLAUDE.md` caveats) the long-term option without building
  it: sub-1100 inference by measuring how much less probable the user's
  moves are than the 1100 band's own median predictability; revisit Maia-2/3
  if the network policy changes.

## Out of scope (other parts)

Sidecars/taxonomy/accuracy (part 1); retry mode and drill deck (part 2);
highlights, opening report, trend-report regeneration, clock analysis, and
regenerating existing game pages (part 4). Existing `games/*.html` are not
touched — the eval graph appears on pages generated from now on (part 4
backfills old pages).

## Deliverables

| File | Change |
|---|---|
| `template.html` | Clickable win% eval graph, two-way synced with the replay |
| `tools/build-progress.*` (new) | Dashboard generator reading `analysis/*.json` |
| `reports/progress.html` (new) | The progress dashboard |
| `games/index.html` | Dashboard link inside the marked tools region |
| `CLAUDE.md` | `evals` field + generation step, Elo display rules + fit exclusions, dashboard regeneration step, extended verification |
| `analysis/*.json` | `eloFit.flat` / `eloFit.floor` flags where recomputed |

## Verification

- **Graph** (Playwright): on a page with `evals`, the graph renders with one
  x-step per ply; clicking a mistake dot equals clicking its card
  (`getPly()` lands on the mistake ply, `#fb-panel` gains `mistake-active`);
  clicking mid-graph jumps the replay; stepping the replay moves the cursor.
  On the existing 2026-07-14 and 2026-07-15 pages (no `evals`), no graph and
  `window.__review.error === null`.
- **Scale sanity**: all graph y-values within [0,100]; a mate-for-user ply
  plots near 100, mate-against near 0.
- **Dashboard**: regenerating twice from the same sidecars is
  byte-identical; every game link resolves; the tag table's per-game counts
  sum to each sidecar's mistake count; series length equals the number of
  sidecars.
- **Elo rule**: feed the 2026-07-15 sidecar through the new rule and assert
  it renders `"≤1100"` or `"unclear"`, not `"≈1900"`; a synthetic
  clearly-peaked fit still yields a band number.
- Commit conventions: work on whatever branch the session designates;
  separate commits for the graph, the dashboard, and the Elo rules; push
  when done.
