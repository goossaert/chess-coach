# Learning Loop 1 of 4 — Foundation: Sidecars, Taxonomy, Accuracy & Drill Links

**Series**: this is part 1 of the four-part *faster learning loop* series, a
split of one master plan into independently runnable phases. Run the parts
**sequentially, one fresh session each** — each part builds on the previous
one's outputs:

1. `docs/0005-plan-learning-loop-1-foundation.md` — **this plan**
2. `docs/0006-plan-learning-loop-2-practice.md` — retry mode + personal drill deck
3. `docs/0007-plan-learning-loop-3-insight.md` — eval graph, progress dashboard, honest Elo
4. `docs/0008-plan-learning-loop-4-polish.md` — highlights, opening report, trend regen, clocks, backfill

**Prerequisites for this part: none** — it starts from the repo as-is.

## The goal behind the whole series

The user's request, restated:

> My goal is to speed up how I learn from my mistakes, and find exercises and
> advice to work on my mistakes and gaps as quickly as possible to improve my
> chess skills and Elo.

Inspiration comes from Lichess.org game analysis (accuracy score, move
annotations, "Learn from your mistakes") and maiachess.com (rating-band
modeling, personalized training). The yardstick for every change: *does it
shorten the path from "game played" to "gap identified, drilled, and
closed"?*

## Context — what this repo is (self-contained, read this first)

`goossaert/chess-coach` turns uploaded chess games (PGN) into interactive
coaching pages. The workflow lives in `CLAUDE.md`, currently **version 2 plus
per-move arrows** (`docs/0003-plan-maia-engine.md`,
`docs/0004-plan-per-move-arrows.md`):

- **Stockfish pass** (depth 20 via `python-chess` + `/usr/games/stockfish`):
  for every user move — eval before, engine best + its eval, eval after the
  played move, swing; the best move is kept for **every** user move (it feeds
  the `moveNotes` per-move arrows). Evals always from the user's perspective.
- **Maia human-model pass** (`tools/maia/` — Maia-1 rating-band networks
  1100–1900, run through zerofish WASM lc0 in headless Chromium; `pip install
  maia3` and the Maia-2/3 checkpoints are **blocked by the sandbox proxy**):
  per-band move probabilities and human-outcome expected scores. Feeds
  `estimatedElo`, `phaseElo`, per-mistake `playedPopularity` /
  `bestFindability` / `expectedPointsLost` / `recurrenceRisk`, a mandatory
  `humanBest` on every user move, and swing×recurrence mistake selection.
- **Output**: one self-contained page per game in `games/`, generated from
  `template.html` by replacing only the `const GAME = {…};` block and
  `<title>`. Raw PGN saved verbatim to `pgn/<same stamp>.txt`.
  `games/index.html` lists all pages. Verification is headless Playwright
  (pre-installed Chromium, `NODE_PATH=/opt/node22/lib/node_modules`, use
  `.cjs` scripts — ESM doesn't see `NODE_PATH`) against `window.__review`
  hooks.

**Design principles (non-negotiable, apply to every part of the series):**

- All GAME schema additions are **optional fields**; the template must render
  existing pages unchanged when new fields are absent.
- Stockfish is the only evaluator; Maia only supplies probabilities and
  human-outcome scores. Never blend them into one number.
- UI changes go in `template.html` (or new standalone files), never in
  generated pages. `games/index.html` edits stay inside marked regions.
- Everything runs inside this sandbox: no external JS/CDNs in pages; no
  direct lichess.org fetches (blocked — reuse the verified URL list in
  `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.md` or
  verify via search); system `pip install chess` fails — use the venv recipe
  in `CLAUDE.md`.

### Why this part exists (findings from reviewing the generated pages)

- Coaching prose is strong, but pages give no at-a-glance game shape: no
  accuracy score, no inaccuracy/mistake/blunder tally (Lichess shows these
  immediately).
- `expectedPointsLost` saturates to "±0.00" in already-decided positions —
  the one number meant to translate centipawns into meaning mostly shrugs.
- Takeaways say *what* to drill but link to nothing to actually practice.
- Nothing machine-readable survives after a page ships; the 2026-07-13 trend
  report was a one-off manual effort and recurrence across games cannot be
  counted without re-running engines. **This part's sidecars are the
  foundation the other three parts read.**

## Scope of this part

### 1. Analysis sidecar per game: `analysis/<stamp>.json`

The pipeline already computes everything; persist it. For each game, write a
JSON with the same filename stamp as the page, containing at least:

```jsonc
{
  "game": { "white": "…", "black": "…", "result": "…", "date": "…",
            "event": "…", "opening": "…", "userColor": "white",
            "pgnFile": "pgn/<stamp>.txt", "pageFile": "games/<stamp>.html" },
  "plies": [ {            // one entry per HALF-MOVE of the game
    "ply": 0, "san": "d4", "uci": "d2d4", "user": true,
    "fenBefore": "…",
    "evalBefore": 0.2, "evalAfter": 0.3,      // numeric pawns, user's perspective,
    "evalBest": 0.3, "bestUci": "g1f3",       //   mates encoded as {"mate": 3}
    "swing": -0.1,
    "winBefore": 52.1, "winAfter": 48.7,      // win%, see formulas below
    "humanBestUci": "g1f3",                   // user moves on Maia pages
    "maia": { "1100": { "played": 0.31, "best": 0.22 }, "…": {} }
  } ],
  "accuracy": { "game": 87.2, "acpl": 34,
    "quality": { "inaccuracies": 3, "mistakes": 2, "blunders": 1 },
    "phases": { "opening": {"accuracy": 94.0, "plies": 20}, "middlegame": {}, "endgame": {} } },
  "eloFit": { "best": 1100, "flat": true, "logProbByBand": { "1100": -1.9, "…": 0 } },
  "mistakes": [ { /* every GAME mistake field, plus: */ "tags": ["conversion-drift"],
                  "fenBefore": "…", "playedUci": "…", "bestUci": "…", "humanBestUci": "…" } ]
}
```

Exact key names may be refined during implementation, but the sidecar must
contain: per-ply FENs/evals/win%/best-moves, per-band Maia numbers where
computed, the full mistake objects with tags and FENs, accuracy/quality
tallies, and the Elo-fit data. Document the schema in `CLAUDE.md`.

New workflow rule in `CLAUDE.md`: *write the sidecar alongside the page and
commit the three files together* (pgn + html + json).

**Backfill**: re-run the pipeline (Stockfish + Maia; depth 18–20 is fine for
backfill) over every existing game in `pgn/` to produce a sidecar for each —
new files only, no existing page is touched. This gives parts 2–4 full
history from day one.

### 2. Controlled mistake taxonomy

Add `tags: ["…"]` (1–3 per mistake) to each mistake in GAME and sidecar.
Fixed vocabulary so recurrence can be counted across games — seeded from the
six categories the 2026-07-13 report found, refined:

`hanging-piece`, `unsafe-capture`, `wrong-recapture`, `missed-tactic`,
`missed-mate`, `slow-mate`, `king-safety`, `unsafe-king-move`,
`pawn-break-timing`, `conversion-drift`, `promotion-race`,
`endgame-technique`, `opening-principle`, `time-trouble` (reserved until
clock data exists).

The writing step picks tags while writing the explanation (it is already
diagnosing the mechanism — this records the diagnosis). Document the
vocabulary in `CLAUDE.md`; extending it is allowed but deliberate (a rename
means updating old sidecars). During the backfill, assign tags to the
existing games' mistakes by reading their pages' explanations.

*Template*: render tags as small chips on the mistake card next to the
existing `recur-tag`. Optional field, absent = no chips.

### 3. Accuracy score, ACPL, and move-quality tally (Lichess-style)

Computed from the Stockfish pass, no new engine work. Formulas (source:
lichess.org/page/accuracy and the lichess-org/lila repository):

- **Win probability**: `win% = 50 + 50 · (2 / (1 + exp(−0.00368208 · cp)) − 1)`,
  centipawns clamped to ±1000 (mate scores mapped through a large
  `mate_score`, e.g. python-chess `score.score(mate_score=100000)` then
  clamped).
- **Move classification** by win% drop (user's perspective): **inaccuracy**
  ≥ 10, **mistake** ≥ 20, **blunder** ≥ 30 win-percentage points.
- **Per-move accuracy**:
  `103.1668 · exp(−0.04354 · (win%_before − win%_after)) − 3.1669`, clamped
  to [0, 100].
- **Game accuracy**: aggregate as Lichess does — the mean of a
  volatility-weighted mean and the harmonic mean of per-move accuracies (a
  plain mean-of-(weighted, harmonic) is an acceptable approximation; note
  which was used in `analysisNote`).
- **ACPL**: average centipawn loss vs. the engine's best, losses clamped at
  1000.
- Compute all of it **per phase** too, reusing the phase boundaries already
  defined for `phaseElo` (opening ≈ first 10 full moves, endgame from queens
  off / few pieces, middlegame between).

New optional GAME fields:

```js
accuracy: "87%",
acpl: 34,
moveQuality: { inaccuracies: 3, mistakes: 2, blunders: 1 },
phaseAccuracy: { opening: "94%", middlegame: "88%", endgame: "71%" },
```

*Template*: a compact stat strip under the header strength line — accuracy,
ACPL, and the ?! / ? / ?? tally — and per-phase accuracy merged into the
existing phase chips. Unlike `estimatedElo`, these numbers are meaningful on
every game, including engine games.

### 4. Win-probability framing on every mistake

Add to each mistake:

```js
winBefore: "92%", winAfter: "45%",
```

from the conversion above. The feedback panel shows "your winning chances:
92% → 45%" alongside the centipawn compare. **Display rule change**: omit
`expectedPointsLost` when it rounds to ±0.00 instead of printing a shrug —
update the `CLAUDE.md` convention (currently says `"±0.00" ok`) and the
schema comment. Stockfish-derived win% is the honest game-theoretic story;
Maia's `expectedPointsLost` stays as human-opposition flavor when
non-negligible.

### 5. Per-mistake training links

Each mistake ends at "what to retain"; extend it to "where to practice". Map
taxonomy tags to curated Lichess URL families — lift the mapping from the 134
already-verified URLs in `reports/2026-07-13-…md` into a committed reference
file `tools/drill-links.json` (tag → list of {label, url}), e.g.:

- `hanging-piece` → lichess.org/training/hangingPiece
- `missed-mate` / `slow-mate` → lichess.org/training/mateIn1, /mateIn2; lichess.org/practice checkmating section
- `wrong-recapture`, `unsafe-capture` → lichess.org/training/capturingDefender, /fork
- `endgame-technique`, `conversion-drift` → lichess.org/practice pawn/rook endgames; lichess.org/training/rookEndgame
- `king-safety`, `unsafe-king-move` → lichess.org/training/kingsideAttack, /exposedKing
- `promotion-race` → lichess.org/training/advancedPawn, /promotion

New per-mistake field, 1–3 links max (the trend report remains the
exhaustive list):

```js
drillLinks: [{ label: "Hanging pieces — Lichess puzzle theme",
               url: "https://lichess.org/training/hangingPiece" }, …]
```

*Template*: a short link list at the bottom of the feedback panel's takeaways
box, rendered only when present. lichess.org cannot be fetched from the
sandbox — only use URLs from the verified families in the 2026-07-13 report.

## Out of scope (later parts — do not build these now)

Retry-the-position mode and the drill deck (part 2); eval graph, progress
dashboard, Elo display fixes (part 3); highlights, opening report, trend
regeneration, clocks, regenerating old pages (part 4). Do not regenerate any
existing `games/*.html` in this part — backfill produces **sidecars only**.

## Deliverables

| File | Change |
|---|---|
| `CLAUDE.md` | Sidecar step + schema, taxonomy vocabulary, accuracy/win% formulas and fields, `winBefore/After`, ±0.00 omission rule, drillLinks step, extended verification |
| `template.html` | Stat strip, phase-chip accuracy, tag chips, win% row, drill-links list — all rendered only when fields present |
| `analysis/*.json` (new dir) | One sidecar per existing game in `pgn/` (backfill) |
| `tools/drill-links.json` (new) | Tag → verified Lichess URL mapping |
| _(no changes)_ | Existing `games/*.html` pages, `pgn/`, `games/index.html` |

## Verification

- **Template compatibility**: load one pre-v2 page
  (`games/2026-07-14-17-37-maia-600-vs-guest.html`), one v2+arrows page
  (`games/2026-07-15-21-31-emgosr-vs-maia-800.html`), and a test page
  carrying all new fields, headless via Playwright; `window.__review.error`
  null on all; new UI elements appear iff their fields are set; existing
  checks (mistake-card clicks, arrows, legend) still pass.
- **Math**: unit-check win% and accuracy formulas on hand-computed values
  (e.g. cp=0 → 50%, symmetric ±cp); accuracy ∈ [0,100]; blunder count ≥
  count of mistakes with |swing| ≥ 3.0 in each backfilled game.
- **Sidecars**: one JSON per `pgn/*.txt`, filename stamps match; every
  `plies[i].san` replays legally with python-chess; `mistakes[].tags` all
  from the documented vocabulary; every sidecar mistake matches its page's
  GAME mistakes (ply/played/best).
- **Drill links**: every URL in `tools/drill-links.json` appears in the
  2026-07-13 report (or is otherwise verified); every tag in the vocabulary
  has at least one mapping.
- Commit conventions: work on whatever branch the session designates; keep
  sidecar backfill, template changes, and `CLAUDE.md` changes in separate,
  clearly-messaged commits; push when done.
