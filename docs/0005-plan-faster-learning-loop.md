# Faster Learning Loop — Plan

Improvements to the analysis workflow, the generated pages, and the repo's
cross-game tooling so that each analyzed game turns into **targeted practice
faster**. Inspiration drawn from Lichess.org game analysis ("Learn from your
mistakes", accuracy score, advantage graph, move annotations) and from
maiachess.com (rating-band modeling, personalized/human-aware training).

## Context — what this repo is and where it stands

`goossaert/chess-coach` turns uploaded chess games (PGN) into interactive
coaching pages. The workflow lives in `CLAUDE.md` and is currently at
**version 2** (per `docs/0003-plan-maia-engine.md`):

- **Stockfish pass** (depth 20 via `python-chess` + `/usr/games/stockfish`):
  for every user move — eval before, engine best + its eval, eval after the
  played move, swing. Evals always from the user's perspective.
- **Maia human-model pass** (`tools/maia/` — Maia-1 rating-band networks,
  1100–1900 in steps of 100, run through the zerofish WASM lc0 in headless
  Chromium; `maia3` via pip and the Maia-2/3 checkpoints are **blocked by the
  sandbox proxy**, verified 2026-07-15): per-position move probabilities per
  band and a human-outcome expected score. Feeds `estimatedElo`, `phaseElo`,
  per-mistake `playedPopularity` / `bestFindability` / `humanBest` /
  `expectedPointsLost` / `recurrenceRisk`, and swing×recurrence mistake
  selection.
- **Output**: one self-contained page per game in `games/` generated from
  `template.html` (only the `const GAME = {…};` block and `<title>` are ever
  replaced in a generated file; all UI changes go into `template.html` so
  every future page benefits). Raw input saved verbatim to `pgn/<same
  stamp>.txt`. `games/index.html` lists all pages newest-first. Cross-game
  material lives in `reports/` (one manually-built trend report + Lichess
  study checklist from 2026-07-13, see
  `docs/0002-plan-multi-game-trend-analysis.md`). Verification is headless
  Playwright against `window.__review` hooks (pre-installed Chromium,
  `NODE_PATH=/opt/node22/lib/node_modules`).

### The user's request behind this plan

> Check my analysis workflow and the last two analyzed games, and suggest how
> the analysis could be improved in advice, content, and features — drawing
> inspiration from Lichess.org and maiachess.com. **My goal is to speed up how
> I learn from my mistakes, and find exercises and advice to work on my
> mistakes and gaps as quickly as possible to improve my chess skills and
> Elo.**

So the yardstick for every idea below is: *does it shorten the path from
"game played" to "gap identified, drilled, and closed"?*

### What the last two analyzed games show

Reviewed: `games/2026-07-14-17-37-maia-600-vs-guest.html` (win vs Maia 600,
generated **before** v2 — no Maia fields) and
`games/2026-07-15-21-31-emgosr-vs-maia-800.html` (loss vs Maia 800, full v2
data). The coaching **writing** is strong: concrete squares and lines,
memorable one-line diagnoses, imperative takeaways with practice details,
typicality percentages used to steer lesson-vs-habit framing. The gaps are
structural, not editorial:

1. **The advice stops at reading.** Takeaways say *what* to drill ("drill the
   basic queen mates") but the page offers nothing to *do* — no retry-the-
   position mode, no generated exercises, no links from a specific mistake to
   a specific Lichess trainer. Learning stays passive.
2. **No at-a-glance game shape.** There is no eval graph, no accuracy score,
   no inaccuracy/mistake/blunder tally — the reader must click through cards
   to sense where the game swung (Lichess gives all three immediately).
3. **The Elo estimate is unreliable exactly where the user plays.** The
   2026-07-15 page says `estimatedElo: ≈1900` with a note admitting the fit
   is "nearly flat", while the user is losing to Maia 800 — the Maia-1 band
   floor is 1100, the games are engine games (out of Maia's human-vs-human
   distribution), and a 35-move forced endgame dominated the phase fit
   (`endgame: ≈1100 · 35 moves`). The number as displayed teaches nothing and
   may mislead.
4. **`expectedPointsLost` saturates.** Three of four mistakes on the
   2026-07-15 page show "±0.00" because in already-decided positions the
   human expected score barely moves. The one number meant to translate
   centipawns into meaning is mostly a shrug.
5. **Mistakes evaporate after the page ships.** Each page's mistakes are
   hand-written into one HTML file; nothing machine-readable survives. The
   2026-07-13 trend report was a one-off manual effort and is already stale
   (two games behind). Recurrence across games — the heart of "fix my gaps" —
   is re-derived from scratch or not at all.
6. **Nothing tracks progress.** No per-game accuracy/Elo/blunder-rate series
   over time, so the user cannot see whether the training is working.
7. **No positive reinforcement.** Pages only show mistakes; Lichess-style
   highlighting of the best moves played (the 16.Bxd5 piece-win, the clean
   conversion stretches) both motivates and confirms which patterns are
   already learned.
8. **Source PGNs carry no clocks or ratings** (maiachess.com exports are
   headers + movetext only), so time-management analysis is currently
   impossible — worth handling when clock-annotated PGNs (e.g. Lichess
   exports with `%clk`) appear.

## Design principles (carried over, non-negotiable)

- All schema additions are **optional fields**; `template.html` must render
  v1 and v2 pages unchanged when new fields are absent.
- Stockfish stays the only evaluator; Maia only supplies probabilities and
  human-outcome scores. Never blend them into one number.
- UI changes go in `template.html` (or new standalone files), never in
  generated pages.
- Everything must run inside this sandbox: no external JS/CDNs in pages, no
  direct lichess.org fetches (blocked — verify URLs via search results, per
  the 0002 plan), pip/HF restrictions on Maia as noted above.

---

## The improvements

Grouped into four workstreams, each with implementation notes and new schema
fields. Priorities: **P1** = fastest path to the user's stated goal, **P2** =
high value, **P3** = polish.

### Workstream A — machine-readable analysis (the foundation) — P1

**A1. Analysis sidecar per game: `analysis/<stamp>.json`.**
The pipeline already computes everything; persist it. For each game, write a
JSON next to the page (same filename stamp) containing: headers + user color;
per-ply record (SAN, UCI, FEN before, Stockfish eval before/after/best at the
recorded depth, best-move UCI, swing, win% before/after — see B1); per-band
Maia probabilities and values where computed; the selected mistakes with all
GAME fields **plus tags (A2)**; accuracy/ACPL/quality tallies (B1);
estimated-Elo fit data (log-prob per band). Add a workflow step: *write the
sidecar alongside the page and commit the three files together* (pgn + html +
json). Everything in workstreams C and D reads these sidecars instead of
re-running engines — this is what makes the cross-game loop cheap enough to
refresh on every game.

**A2. A controlled mistake taxonomy.**
Add `tags: ["…"]` to each mistake (in GAME and in the sidecar). Fixed
vocabulary so recurrence can be counted across games — seed it from the six
categories the 2026-07-13 report found, refined:

`hanging-piece`, `unsafe-capture`, `wrong-recapture`, `missed-tactic`,
`missed-mate`, `slow-mate`, `king-safety`, `unsafe-king-move`,
`pawn-break-timing`, `conversion-drift`, `promotion-race`,
`endgame-technique`, `opening-principle`, `time-trouble` (reserved until
clock data exists). One to three tags per mistake; the writing step picks
them while writing the explanation (it is already diagnosing the mechanism —
this just records the diagnosis). Document the vocabulary in `CLAUDE.md`;
extending it is allowed but must be deliberate (rename = update old
sidecars).

*Template*: render tags as small chips on the mistake card next to the
existing `recur-tag`. Optional field, absent = no chips.

### Workstream B — richer page content and advice — P1/P2

**B1. Accuracy score, ACPL, and move-quality tally (Lichess-style). — P1**
Compute from the Stockfish pass, no new engine work:

- Convert evals to **win probability** with the Lichess formula:
  `win% = 50 + 50 · (2 / (1 + exp(−0.00368208 · cp)) − 1)`, mate scores
  clamped to ±1000 cp equivalent (formula source: lichess.org/page/accuracy
  and the lila repository).
- Classify each user move by win% drop (Lichess thresholds): **inaccuracy**
  ≥ 10, **mistake** ≥ 20, **blunder** ≥ 30 win-percentage points.
- **Game accuracy**: per-move accuracy
  `103.1668 · exp(−0.04354 · (win%_before − win%_after)) − 3.1669` (clamped
  0–100), aggregated as Lichess does (mean of the weighted mean and the
  harmonic mean); also report plain **ACPL** (average centipawn loss, losses
  clamped at 1000).
- Compute per phase too (reuse the phase boundaries from the Maia pass).

New GAME fields (all optional):

```js
accuracy: "87%",                    // whole game, user only
acpl: 34,                           // average centipawn loss
moveQuality: { inaccuracies: 3, mistakes: 2, blunders: 1 },
phaseAccuracy: { opening: "94%", middlegame: "88%", endgame: "71%" },
```

*Template*: a compact stat strip under the header strength line — accuracy,
ACPL, and the ?! / ? / ?? tally — plus per-phase accuracy merged into the
existing phase chips. This gives the at-a-glance shape (gap 2) and, unlike
`estimatedElo`, it is meaningful on every game including engine games.

**B2. Win-probability framing on every mistake. — P1**
Add `winBefore: "92%"` / `winAfter: "45%"` to each mistake, from B1's
conversion. The feedback panel shows "your winning chances: 92% → 45%"
alongside the centipawn compare. This fixes the `expectedPointsLost`
saturation (gap 4) with a number that always moves: Stockfish-derived win% is
the honest game-theoretic story; Maia's `expectedPointsLost` stays as the
human-opposition flavor when it is non-negligible. Display rule change:
**omit** `expectedPointsLost` when it rounds to ±0.00 instead of printing a
shrug (drop the "±0.00 ok" convention from `CLAUDE.md`).

**B3. Per-mistake training links. — P1**
Each mistake card ends at "what to retain"; extend it to "where to practice".
Map taxonomy tags (A2) to curated Lichess URL families — the 2026-07-13
report already verified 134 of them; lift its mapping into a small reference
table in `CLAUDE.md` (or a `tools/drill-links.json`), e.g.:

- `hanging-piece` → lichess.org/training/hangingPiece
- `missed-mate` / `slow-mate` → lichess.org/training/mateIn1, /mateIn2, lichess.org/practice (checkmating section)
- `wrong-recapture`, `unsafe-capture` → lichess.org/training/capturingDefender, /fork
- `endgame-technique`, `conversion-drift` → lichess.org/practice (pawn/rook endgames), lichess.org/training/rookEndgame
- `king-safety`, `unsafe-king-move` → lichess.org/training/kingsideAttack, /exposedKing
- `promotion-race` → lichess.org/training/advancedPawn, /promotion

New per-mistake field:

```js
drillLinks: [{ label: "Hanging pieces — Lichess puzzle theme",
               url: "https://lichess.org/training/hangingPiece" }, …]
```

*Template*: render as a short link list at the bottom of the feedback panel's
takeaways box. Keep it to 1–3 links per mistake — the trend report remains
the exhaustive list. (URL constraint: lichess.org cannot be fetched from the
sandbox; only use URLs from the verified families already in
`reports/2026-07-13-…md` or verified via search.)

**B4. "What went well" highlights. — P2**
Select 1–3 of the user's best moments per game: engine-best (or
near-best) moves in non-forced positions, with extra weight when Maia says
few peers find them (`findability` low = the user outperformed their band).
New field:

```js
highlights: [{ ply: 30, move: "Bxd5", note: "Punished the pawn grab instantly — only 24% of your level takes the piece here.", arrow: ["e4","d5"] }, …]
```

*Template*: a small "What you did well" section under the mistake list, cards
in a calmer style (gold accent instead of rust), clickable to jump the board
like mistake cards. Motivation matters for training adherence, and knowing
which patterns are *already* learned is real information (gap 7).

**B5. Opening report. — P2**
The games keep starting the same way (two Queen's-Pawn games in the last two
alone). Add a compact opening section: ECO + name (already in the header),
the ply where the game left common theory, and one sentence on the first
improvable opening decision. Detect "left theory" offline via a small local
book — python-chess reads Polyglot books; commit a modest public-domain book
to `tools/book/` (or build a frequency table once from a Lichess database
extract if network policy allows; otherwise judgment + the engine already
covers it). Cross-game: once sidecars exist (A1), note "you've reached this
structure N times" from the stored FENs. New fields:

```js
openingReport: { bookExitPly: 7, note: "…", explorerUrl: "https://lichess.org/analysis" }
```

*Template*: one bordered paragraph between the summary and the mistake list,
rendered only when present.

### Workstream C — active practice: from reading to drilling — P1 (the core of the goal)

**C1. "Retry the position" mode on every mistake (Lichess "Learn from your
mistakes"). — P1**
On each mistake card, a **Retry** button: the board jumps to the position
before the mistake, arrows and eval compare hidden, and the user must *play*
a move — click origin square, click destination (promotion defaults to
queen). The page grades it instantly: the engine best and `humanBest` count
as solved (gold flash + show the full feedback); any precomputed
"acceptable" move (eval within 0.5 of best, same tolerance the workflow
already uses for `humanBest`) counts as good-enough (cream flash + "also
fine — the cleanest was …"); anything else shows rust + "that loses X — try
again" with one retry before revealing.

Implementation that keeps the template engine-free: the **generation
pipeline precomputes the grading**. New per-mistake field:

```js
retry: {
  solutions: ["b2b1q"],             // UCI — engine best + humanBest
  acceptable: ["c1b2", "…"],        // within tolerance, from a MultiPV-5 probe
  legal: ["…", …],                  // full legal-move list in the position
  fen: "…"                          // position before the mistake (redundant safety)
}
```

The template only needs to match the user's from→to click against these
lists — no move generation, no engine in the browser. `legal` lets it
distinguish "illegal, ignore the click" from "legal but bad". The Stockfish
pass gains one `multipv=5` probe per selected mistake (seconds of extra
runtime). Verification: every `retry.solutions[0]` equals the mistake's
`best` in UCI; every listed move is legal per python-chess; Playwright
clicks through one solve and one fail path per page.

This is the single highest-leverage feature for the stated goal: it converts
each page from an article into an exercise set, exactly like Lichess's
post-game "Learn from your mistakes" — but with human-findable solutions
accepted, which Lichess doesn't do.

**C2. The personal drill deck: `drills/index.html`. — P1**
A standing, self-contained page that aggregates **every mistake from every
analyzed game** into a puzzle queue — the maiachess.com idea of
personalized, level-aware training, built from the user's own games:

- Built by a generator script (`tools/build-drills.py` or `.mjs`) that reads
  all `analysis/*.json` sidecars (A1) and emits the page from a new
  `drills-template.html` with a `const DRILLS = […];` data block: one entry
  per mistake — FEN, side to move, `retry` grading lists (C1), tags, source
  game link, and the one-line lesson as the post-solve reveal.
- Front end reuses the C1 board/retry interaction. Queue order: **spaced
  repetition** with a simple Leitner scheme in `localStorage` (same
  iOS-Safari-safe pattern as the 2026-07-13 checklist page: try/catch,
  stable keys — key = game stamp + ply). Solved-easily items retreat, failed
  items return next session. Filters by tag ("only endgame-technique
  today") and a small "due today / solved streak" counter.
- Workflow step: after generating a game page, **regenerate the drill deck**
  and commit it with the page. `games/index.html` gets one link to it above
  the game list (allowed: it's inside the marked list region's surroundings —
  add a second marked region rather than editing unmarked markup).

Together C1+C2 close the loop the user asked for: every mistake becomes a
retryable exercise the same day, and keeps resurfacing until it stops
failing.

### Workstream D — cross-game insight and trust — P2/P3

**D1. Eval graph under the board (Lichess advantage chart). — P2**
A clickable SVG sparkline of the game: x = ply, y = win% (from B1; clamped,
so it never explodes on mate scores), user's perspective, zero-line marked,
mistake plies flagged with rust dots (clicking a dot = clicking the card),
current-ply cursor synced with the replayer both ways. Data comes from a new
optional `evals: [+0.2, +0.3, …]` (or win% array) in GAME, one entry per
ply, written by the pipeline. Renders only when present. This is the biggest
pure-template feature; keep it dependency-free SVG like the board.

**D2. Progress dashboard: `reports/progress.html`. — P2**
Generated from the sidecars (A1) by a small script, refreshed whenever a new
game is analyzed: per-game series over time for accuracy, ACPL,
blunders/game, estimatedElo (with its confidence, see D3), per-phase
accuracy; plus a **tag recurrence table** — for each taxonomy tag, mistakes
per game over the last N games, so the user sees a gap *shrinking* after
drilling it (or not). Self-contained inline-SVG charts, house style. This
answers "is the training working?" (gap 6), which is the feedback signal the
whole loop needs.

**D3. Honest Elo estimation. — P2**
Fix gap 3 rather than widen it:

- When the best-fit band rails at the **floor (1100)** or the fit is flat
  (log-prob spread across bands below a threshold), display `estimatedElo:
  "≤1100"` or `"unclear"` — never a confident-looking middle number. Keep
  `estimatedEloNote` but make the display rule mechanical, decided by the
  pipeline, not by editorial goodwill.
- **Exclude low-information stretches** from the fit: forced/only-move
  positions (already done), and additionally positions where |eval| > ~6
  (dead-won/dead-lost conversion phases — the 35-move endgame that dragged
  the 2026-07-15 fit) unless the phase would otherwise have no sample.
- Add a second, independent strength signal: an **accuracy/ACPL-based
  estimate** from published ACPL↔rating regressions (approximate; label it
  as such), shown only in `estimatedEloNote` as corroboration — e.g. "band
  fit ≤1100 (floor); ACPL 78 is typical of ~900–1100 rapid". Two weak
  signals agreeing beat one flat fit.
- Long-term option, documented but not required: acquire sub-1100 behavior
  by conditioning on the 1100 band and measuring the *gap* (how much less
  probable the user's moves are than the band's median predictability) — or
  revisit Maia-2/3 access if the network policy changes.

**D4. Trend report as a repeatable step. — P3**
Recast the 2026-07-13 report as a generated artifact: a script reads the
sidecars, rebuilds the per-category evidence tables and the scoreboard, and
re-emits the markdown + checkbox-HTML pair (checkbox state keys are
URL-derived, so ticks survive regeneration — that was already designed for in
0002). The curated prose and the Lichess link lists stay in a hand-edited
section the generator preserves. Refresh cadence: on request, or suggested
whenever ≥3 new games have accumulated.

**D5. Clock-aware analysis (dormant until data exists). — P3**
maiachess.com PGNs have no `%clk`; Lichess exports do. Add to `CLAUDE.md`:
if the PGN carries clock comments, parse them (don't strip them from the
saved `pgn/*.txt` — the save-verbatim rule already guarantees this), compute
per-move time spent, render a small time bar in the eval graph (D1), tag
mistakes played fast in critical positions as `time-trouble`, and add a
takeaway about pacing when blunders correlate with <10s moves. Also advise
the user in-chat, once: *when possible, export games from Lichess with
clocks included — it unlocks time-management coaching.*

**D6. Backfill old pages. — P3**
Optionally re-run the pipeline over `pgn/` history to (a) produce sidecars
for all nine existing games so the drill deck and dashboard start with full
history, and (b) regenerate the pre-v2 pages (e.g. the 2026-07-14 Maia-600
game) with Maia + new fields. Sidecar backfill is cheap and safe (new files
only) — do it in Phase 1. Page regeneration overwrites shipped pages — do it
last, one commit per page, after the template changes have proven stable.

---

## Suggested phasing

| Phase | Items | What the user gets |
|---|---|---|
| **1 — Foundation + measurement** | A1 sidecars (incl. D6 backfill of sidecars), A2 taxonomy, B1 accuracy/ACPL/quality, B2 win% framing, B3 drill links | Every new page shows accuracy, honest impact numbers, and practice links; history becomes machine-readable |
| **2 — Active practice** | C1 retry mode, C2 drill deck | Mistakes become exercises with spaced repetition — the core ask |
| **3 — Orientation + feedback signal** | D1 eval graph, D2 progress dashboard, D3 Elo fixes | See each game's shape at a glance and whether training is moving the needle |
| **4 — Polish** | B4 highlights, B5 opening report, D4 trend regeneration, D5 clocks, D6 page regeneration | Rounding out |

Each phase is independently shippable and template changes stay additive
throughout — a page generated after Phase 1 renders fine in a template from
Phase 3.

## Deliverables

| File | Change |
|---|---|
| `CLAUDE.md` | Workflow v3: sidecar step, taxonomy vocabulary, accuracy/win% formulas, retry precompute, drill-deck regeneration step, new GAME fields, extended verification, display rules (±0.00 omission, Elo floor rule) |
| `template.html` | Stat strip, win% rows, tag chips, drill links, retry mode, highlights section, opening report block, eval graph — all rendered only when fields present |
| `analysis/` (new) | One JSON sidecar per game (and backfill for the nine existing games) |
| `drills-template.html` + `drills/index.html` (new) | The personal drill deck |
| `tools/build-drills.*`, `tools/build-progress.*` | Generators reading `analysis/*.json` |
| `reports/progress.html` (new) | Progress dashboard |
| `games/index.html` | A link to the drill deck (new marked region) |
| `docs/0005-plan-faster-learning-loop.md` | This plan |

## Verification (extends the existing step-6 checks)

- **Schema compatibility**: load one v1 page (2026-07-14), one v2 page
  (2026-07-15), and one new-schema page headless; `window.__review.error`
  null on all three; new UI elements appear iff their fields are set.
- **Accuracy math**: unit-check the win%/accuracy formulas against a few
  known Lichess-analyzed positions (hand-computed from the published
  formulas); assert accuracy ∈ [0,100] and blunder count ≥ number of
  mistakes with swing ≥ 3.0 in sampled games.
- **Retry mode**: for every mistake, `retry.solutions` ⊆ `retry.legal`, all
  UCI legal per python-chess in the FEN before the ply; Playwright plays one
  solving move and one failing move per page and asserts the grade classes.
- **Drill deck**: item count equals total mistakes across sidecars; tick a
  drill as solved, reload, assert the Leitner state survived (localStorage,
  same pattern the 0002 checklist verified on iOS Safari).
- **Dashboard/report generators**: regenerate twice from the same sidecars →
  byte-identical output (determinism); every game link resolves.
- **Elo display rule**: feed the 2026-07-15 sidecar through the new rule and
  assert it renders "≤1100"/"unclear" rather than "≈1900".

## Caveats a fresh session must know

- **Sandbox network**: `pip install maia3` and the Maia-2/3 checkpoints are
  blocked; Maia-1 runs via `tools/maia/setup.sh` (vendor/weights are
  gitignored, re-fetched per session). lichess.org cannot be fetched
  directly — verify links via search or reuse the already-verified list in
  `reports/2026-07-13-…md`. System `pip install chess` fails — use the venv
  recipe in `CLAUDE.md`.
- **Engine-opponent bias**: most `pgn/` games are vs. engines; Maia
  probabilities in engine-created positions carry extra noise, and win%
  numbers describe perfect-play truth, not practical chances vs. Maia 600.
  Keep the existing grain-of-salt language.
- **Template discipline**: never edit markup/CSS/JS in generated pages; all
  new UI is additive and feature-flagged by field presence. Keep
  `games/index.html` edits inside marked regions.
- **Commit convention**: page + pgn + sidecar (+ regenerated drill deck /
  index) commit together; work on `main` was explicitly authorized for this
  plan's documentation pass — implementation sessions should follow whatever
  branch instruction they are given.
