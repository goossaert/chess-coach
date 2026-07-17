# Learning Loop 2 of 4 — Active Practice: Retry Mode & the Personal Drill Deck

**Series**: part 2 of the four-part *faster learning loop* series. Run the
parts sequentially, one fresh session each:

1. `docs/0005-plan-learning-loop-1-foundation.md` — sidecars, taxonomy, accuracy, drill links
2. `docs/0006-plan-learning-loop-2-practice.md` — **this plan**
3. `docs/0007-plan-learning-loop-3-insight.md` — eval graph, progress dashboard, honest Elo
4. `docs/0009-plan-learning-loop-4-polish.md` — highlights, opening report, trend regen, clocks, backfill

**Prerequisites — verify before starting**: part 1 must be complete.
Check that `analysis/` contains one `.json` sidecar per `pgn/*.txt` game
(matching filename stamps) with per-mistake `fenBefore`, `playedUci`,
`bestUci`, `humanBestUci`, and `tags`; and that `CLAUDE.md` documents the
sidecar step, the taxonomy vocabulary, and the accuracy fields. If any of
that is missing, **stop and run the 0005 plan first**.

## Goal

The user's stated goal for the series: *speed up learning from mistakes; get
exercises to work on gaps as quickly as possible.* This part is the core of
that goal: it converts each review page from an article into an exercise set
(Lichess's "Learn from your mistakes", but accepting human-findable
solutions), and aggregates every mistake ever analyzed into a standing
spaced-repetition drill deck (the maiachess.com idea of personalized
training, built from the user's own games).

## Context — repo essentials (self-contained)

`goossaert/chess-coach` turns PGN games into interactive coaching pages. The
workflow in `CLAUDE.md` (version 2 + per-move arrows + part-1 foundation)
runs a Stockfish pass (depth 20, `python-chess` + `/usr/games/stockfish`,
evals from the user's perspective) and a Maia rating-band pass
(`tools/maia/`, bands 1100–1900 via zerofish WASM lc0 in headless Chromium),
then generates one self-contained page per game in `games/` from
`template.html` (only the `const GAME = {…};` block and `<title>` are
replaced in generated files). Each page's `mistakes` carry ply, played/best
SAN, evals, swing, arrows, Maia typicality fields, a mandatory `humanBest`,
`tags`, `winBefore/After`, `drillLinks`, and takeaways. Sidecars in
`analysis/` persist everything machine-readable. Verification is headless
Playwright (`NODE_PATH=/opt/node22/lib/node_modules`, `.cjs` scripts — ESM
doesn't see `NODE_PATH`) against `window.__review` hooks.

**Design principles (non-negotiable):** new GAME fields are optional — the
template renders old pages unchanged; Stockfish is the only evaluator (Maia
supplies probabilities only); UI changes go in `template.html` or new
standalone files, never in generated pages; `games/index.html` edits stay
inside marked regions; no external JS/CDNs; no direct lichess.org fetches;
system `pip install chess` fails — use the venv recipe in `CLAUDE.md`.

## Scope of this part

### 1. "Retry the position" mode on every mistake (template + pipeline)

On each mistake card, a **Retry** button: the board jumps to the position
before the mistake, arrows and eval compare hidden, and the user must *play*
a move — click origin square, then destination (promotions default to
queen). The page grades instantly:

- move ∈ `solutions` (engine best, `humanBest`) → solved: gold flash, then
  reveal the full feedback;
- move ∈ `acceptable` (eval within 0.5 of best) → good-enough: cream flash +
  "also fine — the cleanest was …";
- any other legal move → rust flash + "that loses X — try again", one retry
  before revealing;
- not in `legal` → ignore the click (illegal move, not an answer).

The template stays **engine-free**: the generation pipeline precomputes the
grading. New per-mistake GAME field:

```js
retry: {
  fen: "…",                       // position before the mistake (redundant safety)
  solutions: ["b2b1q"],           // UCI — engine best + humanBest (deduped)
  acceptable: ["c1b2", "…"],      // within 0.5 of best, from a MultiPV-5 probe
  legal: ["…", …]                 // full legal-move list in the position
}
```

Pipeline change (`CLAUDE.md` step 2): one Stockfish `multipv=5` probe per
selected mistake (seconds of extra runtime); `acceptable` = the probed moves
whose eval stays within 0.5 of best (evals clamped to ±10 pawns before
comparing, mates through `mate_score` — same clamping the human-findable
scan already uses). `legal` from python-chess. Also **store the `retry`
object in the sidecar mistake entries** so the drill deck (below) can reuse
it without re-running engines.

Template interaction notes: reuse the existing board renderer and arrow
layer; add a from/to click handler active only in retry mode; expose test
hooks (`window.__review.retryStart(i)`, `retryPlay(uci)`, `retryState()`)
for verification. All retry UI renders only when the mistake has a `retry`
field — old pages keep working.

### 2. The personal drill deck: `drills/index.html`

A standing, self-contained page aggregating **every mistake from every
analyzed game** into a puzzle queue:

- **Generator**: `tools/build-drills.py` (venv python; or `.cjs` node) reads
  all `analysis/*.json` sidecars and emits `drills/index.html` from a new
  committed `drills-template.html` by replacing a marked
  `const DRILLS = […];` block (same replace-only-the-data-block discipline
  as `template.html`). One entry per mistake: `fen`, side to move, the
  `retry` grading lists, `tags`, source game link (`games/<stamp>.html`),
  the mistake's one-line `title` as the post-solve reveal, and the first
  takeaway lesson. For sidecars that predate the `retry` field (part-1
  backfill), the generator computes it itself: legal moves via python-chess,
  `solutions`/`acceptable` via a quick Stockfish multipv=5 probe of the
  stored FEN (depth 18 is fine), then writes the computed `retry` back into
  the sidecar so the probe runs once ever.
- **Front end**: house style (same fonts/colors as `template.html`); reuses
  the retry board interaction from item 1 (a trimmed copy inside
  `drills-template.html` is acceptable — the two templates are separate
  self-contained files by design). Queue order: **spaced repetition** via a
  simple Leitner scheme in `localStorage` — key = `<stamp>:<ply>` (stable
  across regenerations), boxes 1–4, failed → box 1 (due immediately next
  session), solved → next box (due in 1/3/7 days). iOS-Safari-safe storage:
  try/catch around all access, real `<input>`/button `change`/`click`
  events, no external JS — the same pattern
  `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.html`
  already uses.
- **UI**: "due today" counter, solved-streak counter, filter by tag ("only
  endgame-technique today"), and per-drill a link back to the source game
  page.
- **Workflow step** (`CLAUDE.md`): after generating a game page + sidecar,
  **re-run the drill generator** and commit `drills/index.html` with the
  page. `games/index.html` gets one link to the drill deck — add it inside a
  **new marked region** (e.g. `<!-- TOOLS -->…<!-- END TOOLS -->`) above the
  game list rather than editing unmarked markup; document the region in
  `CLAUDE.md`.

## Out of scope (other parts)

Accuracy/taxonomy/sidecar schema (part 1, already done); eval graph,
progress dashboard, Elo display rules (part 3); highlights, opening report,
trend-report regeneration, clock analysis, regenerating old game pages
(part 4). Existing `games/*.html` pages are **not** regenerated in this
part — retry mode appears on pages generated from now on, while the drill
deck covers all history via the sidecars.

## Deliverables

| File | Change |
|---|---|
| `template.html` | Retry mode (button, click-to-move input, grading states, test hooks) |
| `drills-template.html` (new) | Drill-deck template with marked `DRILLS` data block |
| `drills/index.html` (new) | Generated deck covering every sidecar mistake |
| `tools/build-drills.*` (new) | Deck generator (also backfills `retry` into old sidecars) |
| `analysis/*.json` | `retry` objects added to mistake entries |
| `games/index.html` | Drill-deck link in a new marked region |
| `CLAUDE.md` | `retry` precompute in step 2, `retry` schema field, drill-deck regeneration step, extended verification |

## Verification

- **Retry data**: for every mistake with `retry`: `solutions ⊆ legal`,
  `acceptable ⊆ legal`, `solutions ∩ acceptable = ∅`, every UCI legal per
  python-chess in `retry.fen`, and `retry.solutions` contains the mistake's
  `best` in UCI.
- **Retry UI** (Playwright, on a page generated with the new schema): start
  retry on a mistake → arrows/compare hidden; play a solution → solved
  state + feedback revealed; reload, play a bad legal move twice → reveal;
  clicking squares of an illegal move changes nothing. Old pages
  (2026-07-14, 2026-07-15) still load with `window.__review.error === null`
  and show no retry button.
- **Drill deck**: entry count equals total mistakes across all sidecars;
  every source-game link resolves to a file in `games/`; solve one drill,
  reload, assert its Leitner state survived (localStorage); fail one drill,
  assert it is due again; tag filter shows only matching drills; no console
  errors headless.
- **Determinism**: running `tools/build-drills.*` twice in a row produces
  byte-identical `drills/index.html`.
- Commit conventions: work on whatever branch the session designates;
  separate commits for template retry mode, drill generator + deck, and
  `CLAUDE.md`; push when done.
