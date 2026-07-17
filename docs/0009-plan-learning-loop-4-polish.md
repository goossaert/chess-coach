# Learning Loop 4 of 4 — Polish: Highlights, Openings, Trend Regen & Clocks

**Series**: part 4 (final) of the *faster learning loop* series. Run the
parts sequentially, one fresh session each:

1. `docs/0005-plan-learning-loop-1-foundation.md` — sidecars, taxonomy, accuracy, drill links
2. `docs/0006-plan-learning-loop-2-practice.md` — retry mode + personal drill deck
3. `docs/0007-plan-learning-loop-3-insight.md` — eval graph, progress dashboard, honest Elo
4. `docs/0009-plan-learning-loop-4-polish.md` — **this plan**

**Prerequisites — verify before starting**: parts 1–3 complete. Check for:
`analysis/*.json` sidecars (one per `pgn/*.txt`), `drills/index.html` +
`tools/build-drills.*`, `reports/progress.html` + `tools/build-progress.*`,
the eval-graph `evals` field and retry mode in `template.html`, and their
documentation in `CLAUDE.md`. If anything is missing, run the corresponding
earlier plan first.

Backfilling the pre-existing pages onto the current template used to be
item 5 of this plan; it now lives in its own plan,
`docs/0010-plan-single-game-backfill.md`, which regenerates **one game
per request** (and can run in parallel across games). Run this plan first
so the template is stable, then invoke plan 0010 per game.

## Goal

The user's stated goal for the series: *speed up learning from mistakes and
improve Elo.* Parts 1–3 built measurement, practice, and feedback. This part
rounds out the coaching content (reinforce what already works, cover the
opening phase, keep the cross-game report alive, prepare for clock data).
Bringing the pre-existing pages up to the new standard is handled
separately, one game at a time, by
`docs/0010-plan-single-game-backfill.md`.

## Context — repo essentials (self-contained)

`goossaert/chess-coach` turns PGN games into interactive coaching pages. The
workflow in `CLAUDE.md` runs a Stockfish pass (depth 20, `python-chess` +
`/usr/games/stockfish`, evals from the user's perspective) and a Maia
rating-band pass (`tools/maia/`, Maia-1 bands 1100–1900 via zerofish WASM
lc0 in headless Chromium; `pip install maia3` / Maia-2/3 checkpoints blocked
by the sandbox proxy), then generates one page per game in `games/` from
`template.html` (only the `const GAME = {…};` block and `<title>` are
replaced in generated files; the raw PGN is saved **verbatim** to
`pgn/<stamp>.txt`). Sidecars in `analysis/` persist everything; the drill
deck (`drills/`) and progress dashboard (`reports/progress.html`) are
regenerated from them after each game. `games/index.html` lists all pages
(edits only inside marked regions). Verification is headless Playwright
(`NODE_PATH=/opt/node22/lib/node_modules`, `.cjs` scripts) against
`window.__review` hooks.

**Design principles (non-negotiable):** new GAME fields are optional — the
template renders old pages unchanged; Stockfish is the only evaluator, Maia
supplies probabilities and human-outcome scores only; UI changes go in
`template.html` or standalone files, never hand-edited into generated pages;
no external JS/CDNs; **lichess.org cannot be fetched from the sandbox** —
verify URLs via search or reuse the verified list in
`reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.md`; system
`pip install chess` fails — use the venv recipe in `CLAUDE.md`.

## Scope of this part

### 1. "What went well" highlights

Pages currently show only mistakes. Select 1–3 of the user's best moments
per game: engine-best (or near-best) moves in **non-forced** positions,
weighted up when Maia says few peers find them (low findability = the user
outperformed their band). New optional GAME field:

```js
highlights: [{ ply: 30, move: "Bxd5",
  note: "Punished the pawn grab instantly — only 24% of your level takes the piece here.",
  arrow: ["e4","d5"] }, …]
```

*Template*: a small "What you did well" section under the mistake list —
cards in a calmer style (gold accent instead of rust), clickable to jump the
board exactly like mistake cards. *Pipeline*: selection criteria in
`CLAUDE.md` (non-forced, played ≈ best, prefer low `bestFindability`, spread
across phases); store highlights in the sidecar too, so the dashboard could
later count them.

### 2. Opening report

The user's games keep starting the same way (recent games are all
Queen's-Pawn structures). Add a compact opening section between the summary
and the mistake list:

```js
openingReport: {
  bookExitPly: 7,
  note: "…one sentence on the first improvable opening decision…",
  explorerUrl: "https://lichess.org/analysis"   // or an opening-explorer URL from the verified families
}
```

"Left theory" detection must work offline: python-chess reads Polyglot
books — commit a modest public-domain book under `tools/book/` if one can be
obtained through the proxy; otherwise fall back to judgment + the engine
pass (say which in `analysisNote`). Cross-game (sidecars exist now): when
the same opening/first-N-ply FEN sequence has occurred in ≥2 sidecars, say
so in the note ("you've reached this structure N times — worth 20 minutes of
study"). *Template*: one bordered paragraph, rendered only when the field is
present.

### 3. Trend report as a repeatable step

Recast the one-off 2026-07-13 report as a generated artifact:

- A `tools/build-trend-report.*` script reads all sidecars and rebuilds the
  data-driven parts of the report: the per-game scoreboard, the
  per-category (taxonomy-tag) evidence tables with game/move/cost, ordered
  by aggregate cost. The curated prose and the Lichess link lists live in a
  hand-edited section/template the generator **preserves verbatim** across
  regenerations (marked regions, same discipline as `games/index.html`).
- Output: refresh `reports/<date>-recurring-mistakes-and-lichess-study-plan`
  (`.md` + checkbox `.html` pair). The HTML's checkbox state keys are
  URL-derived (designed in `docs/0002-plan-multi-game-trend-analysis.md`
  precisely so ticks survive regeneration) — keep that keying.
- Cadence rule in `CLAUDE.md`: regenerate on request, and suggest it to the
  user whenever ≥3 games have accumulated since the last regeneration.

### 4. Clock-aware analysis (dormant until data exists)

PGNs from maiachess.com carry no clock data; Lichess exports do (`%clk`
comments). Add to `CLAUDE.md` (workflow + schema), guarded by "if the PGN
carries clock comments":

- Parse per-move time spent (the verbatim-save rule already preserves the
  comments in `pgn/*.txt`; note in `CLAUDE.md` that step 1's
  "strip comments" applies to the **movetext parsing only**, never to the
  saved file).
- Add a thin time bar under the eval graph (part 3's SVG — extend it), a
  `timeSpent` array field mirroring `evals`, and tag mistakes played fast in
  critical positions with the reserved `time-trouble` taxonomy tag; write a
  pacing takeaway when blunders correlate with <10s moves.
- Tell the user, once, in the session that implements this: *export games
  from Lichess with clocks included — it unlocks time-management coaching.*
- Template/time-bar work can ship before any clock data exists (renders only
  when `timeSpent` is present); verify with a synthetic test page.

## Out of scope

Everything already delivered in parts 1–3. No new analysis passes beyond
what the items above name; no template redesign; no index restructuring
beyond the existing marked regions.

## Deliverables

| File | Change |
|---|---|
| `template.html` | Highlights section, opening-report block, time bar (renders only when fields present) |
| `CLAUDE.md` | Highlights + openingReport + clock schema/steps, trend-report cadence rule, backfill notes |
| `tools/build-trend-report.*` (new) | Trend-report generator over sidecars |
| `reports/…-recurring-mistakes-…{md,html}` | Regenerated, curated sections preserved, checkbox keys stable |
| `tools/book/` (new, optional) | Offline opening book if obtainable |
| `analysis/*.json` | Highlights (and any newly computed fields) added |

Regenerating the pre-existing `games/*.html` pages (and the drill deck /
dashboard afterward) is delivered by `docs/0010-plan-single-game-backfill.md`,
one game per request.

## Verification

- **Highlights/opening/time UI**: on a synthetic page carrying all three
  fields — highlight cards jump the board like mistake cards; the opening
  block renders; the time bar renders iff `timeSpent` is present. On a page
  without them: absent, `window.__review.error === null`.
- **Trend report**: regenerate twice → data tables byte-identical and the
  curated sections untouched (diff against the pre-regeneration file);
  every checkbox key unchanged for URLs that persist; per-tag costs
  reconcile with the sidecars.
- Commit conventions: work on whatever branch the session designates;
  separate commits for template/tooling/docs; push when done. (Page
  backfill and its verification are covered by
  `docs/0010-plan-single-game-backfill.md`.)
