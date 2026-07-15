# Maia-3 Human-Model Analysis — Plan

## Context

This repo (`goossaert/chess-coach`) turns chess games into interactive coaching pages.
The user uploads a game in PGN format; the workflow (defined in `CLAUDE.md`) parses it,
analyzes every user move with **Stockfish** via `python-chess` (depth 20, evals from the
user's perspective), selects the 3–6 biggest mistakes by eval swing, writes coaching
content for each, and generates one self-contained HTML page per game in `games/` by
copying `template.html` and replacing only its marked `const GAME = { … };` data block.
The raw PGN is saved to `pgn/` with a matching filename, and `games/index.html` lists
every page. Each page shows a replayable SVG board, a feedback panel, and clickable
mistake cards with a swing badge, a before/played/best 3-column eval compare, rust
(played) and gold (engine best) arrows, and "What to retain" takeaways. Cross-game
trend reports live in `reports/` (see `docs/0002-plan-multi-game-trend-analysis.md`).

The games analyzed so far are the user (playing as "Anonymous"/"Guest") vs. Stockfish
levels and vs. maia-600 on Lichess; the PGNs carry no Elo (`WhiteElo "?"`), so nothing
in the current pipeline knows the user's actual strength.

### The user's request

> Could the current analysis framework/steps be improved if they were to include the
> Maia-3 AI as part of the analysis in addition to the Stockfish engine? If so how so,
> and what additional value or sections should be added to the existing analysis
> template and process?

A follow-up instruction for this plan: **all five points from "What it would add to the
analysis" must be incorporated as UI changes that are visible and usable by the user**
on the generated pages — not just as internal pipeline metrics.

## Assessment

**Yes — and the improvement is structural, not incremental.** Stockfish and Maia-3
answer different questions: Stockfish tells you *what the truth of the position is*;
Maia-3 tells you *what a human at a given rating actually plays there*. The current
framework is built entirely on the first axis (eval swings → 3–6 biggest mistakes), and
everything a coach would say about typicality, findability, and recurrence risk is
currently being guessed at in the written explanations. Maia-3 lets the pipeline
measure those things.

### What Maia-3 is (facts a fresh session needs)

- Released 2026 by the CSSLab (University of Toronto — the group behind the original
  Maia), Maia-3 is a family of **"Chessformer"** encoder-only transformer models
  (5M/23M/79M parameters) that predict the human move ~57% of the time on a standard
  test set (vs. 52.0% for Maia-2, 51.6% for Maia-1), **conditioned on player and
  opponent Elo from 600 to 2600**.
- It is a **move predictor, not an evaluator**: it emits a probability distribution
  over legal moves for a given rating band, plus **WDL values derived from human game
  outcomes** (win/draw/loss expectancy against human opposition at that level).
- Install: `pip install maia3` (AGPL-3.0 — fine here, generated pages only embed its
  *outputs*). Checkpoints download from Hugging Face on first run and are cached.
  Runs fine on CPU; preset CLI aliases `maia3-5m`, `maia3-23m`, `maia3-79m`.
- It exposes a **UCI engine** with MultiPV and WDL output, so it slots into the exact
  same `python-chess` loop `CLAUDE.md` already uses for Stockfish:

  ```python
  import chess.engine
  maia = chess.engine.SimpleEngine.popen_uci(["maia3-uci", "--model", "maia3-23m"])
  # rating conditioning via --elo (player and opponent Elo); MultiPV ~5 for the
  # human-move probability distribution at a position.
  ```

- Sources: [Maia-3 GitHub (CSSLab/maia3)](https://github.com/CSSLab/maia3),
  [Introducing Maia-3 — Ashton Anderson's blog](https://vuink.com/post/yvpurff-d-dbet/@/ashtonanderson/blog/introducing-maia-3-free-and-open-source/vCPPRtX3),
  [Maia Chess project site](https://www.maiachess.com/),
  [Maia3-79M on Hugging Face](https://huggingface.co/UofTCSSLab/Maia3-79M),
  [original Maia repo](https://github.com/CSSLab/maia-chess).

### What it would add to the analysis

Ranked by coaching value:

1. **Typicality of each mistake — "is this a knowledge gap or a lapse?"**
   For every mistake Stockfish finds, query Maia-3 at the user's level for the
   probability of the played move. A blunder that 40% of similarly-rated players also
   make is a *pattern worth drilling* (the position itself is a trap for that level);
   a blunder only 2% would make is an *attention/discipline lapse*, and the takeaway
   should be a blunder-check habit, not an opening lesson. The `takeaways` currently
   can't distinguish these two cases; this is the single biggest coaching upgrade
   available.

2. **Findability of the "best" move — stop recommending engine-only moves.**
   The gold arrow currently shows Stockfish's top choice, which is sometimes a move no
   human under 2600 would find. With Maia-3, check the human probability of the
   engine's best move; when it's near zero, the page should instead highlight the best
   *human-findable* alternative — the highest-Maia-probability move among those that
   keep the eval within tolerance of best. Telling a club player "you should have
   played the quiet prophylactic Qb1" when 0.5% of 2600s would find it is
   anti-coaching; "Nf5 was also winning and half the players at your level see it" is
   actionable.

3. **Smarter mistake *selection*, not just annotation.**
   The current criterion is "largest negative swing." A better rank is roughly
   **swing × recurrence likelihood**: a −1.5 mistake that the user's rating band plays
   35% of the time in that structure is more instructive than a −3.0 one-off. (Moves
   allowing mate still always qualify, as now.)

4. **Estimated playing strength — especially valuable for *this* repo.**
   Every game in `pgn/` has no rating anywhere. By sweeping Maia-3's Elo conditioning
   and finding which rating band best predicts the user's actual moves, the pipeline
   gets a per-game (and per-phase: opening/middlegame/endgame) strength estimate
   ("you played this game like a ~1350, but your endgame moves matched ~1100"). It
   also makes the cross-game work in `reports/` far more grounded — including tracking
   improvement over time.

5. **Human-meaningful eval deltas.**
   Maia-3's WDL comes from human game outcomes, so swings can be expressed as
   *expected-points cost against human opposition at your level* ("this move cost you
   ~18% of a point") alongside the centipawn number. Centipawns mean little to most
   improving players; expected score is the number coaches actually reason with.

## Deliverables

| File | Purpose |
|---|---|
| `template.html` | Extended to render the new Maia-driven GAME fields (all five points above surfaced in the UI; additive, so existing pages stay valid) |
| `CLAUDE.md` | Workflow updated: Maia-3 setup, second analysis pass, new selection criterion, new schema fields, extended verification |
| `docs/0003-plan-maia-engine.md` | This plan |

Generated pages pick up the new sections automatically the next time a game is
analyzed; existing pages in `games/` are not regenerated as part of this work.

## 1. GAME schema additions

Additive fields, so existing pages stay valid (the template must render cleanly when
they are absent):

```js
mistakes: [{
  // existing fields unchanged (ply, played, best, evalBefore, evalAfter,
  // evalBest, swing, title, explanation, playedArrow, bestArrow, takeaways), plus:
  playedPopularity: "38%",        // Maia-3: share of your level playing your move
  bestFindability: "6%",          // Maia-3: share of your level finding engine best
  humanBest: "Nf5",               // best human-findable move, shown when engine best
  humanBestArrow: ["d3","f5"],    //   is "unfindable"; omitted when best === humanBest
  humanBestFindability: "47%",    // share of your level that finds humanBest
  expectedPointsLost: "0.21",     // WDL-based swing at your level (expected score)
  recurrenceRisk: "high",         // "high" | "medium" | "low" — drives the card tag
}],
// page-level:
estimatedElo: "≈1300",            // Maia-3 best-fit rating band for this game
phaseElo: { opening: "≈1450", middlegame: "≈1300", endgame: "≈1100" },
```

Conventions stay as they are: evals from the user's perspective, minus sign `−` in
displayed values, `analysisNote` in the footer — now naming both engines, e.g.
"Stockfish 16 depth 20 · Maia-3-23M conditioned at ≈1300".

## 2. UI changes (`template.html`)

Per the repo's own rule, all UI changes go in `template.html` so every future page
benefits; never edit markup in generated files. Each of the five analysis points maps
to a visible, usable element:

- **(1) Typicality badge** — on each mistake card *and* in the feedback panel's mistake
  header, next to the existing swing badge: e.g. **"common at your level — 38% play
  this"** (rust-tinted) vs. **"uncharacteristic slip — 2%"** (neutral), driven by
  `playedPopularity`. The "What to retain" box already branches in *content* (drill
  vs. habit — written at generation time); the badge makes the diagnosis legible at a
  glance.
- **(2) Findability row + human-best arrow** — a row under the existing
  before/played/best 3-column compare showing `bestFindability` (and
  `humanBestFindability` when present): "6% of players at your level find Qb1 —
  Nf5 keeps the win and 47% see it." When `humanBest` differs from `best`, draw a
  **third arrow** for `humanBestArrow` in a distinct color (e.g. a lighter gold /
  cream), and add it to the board legend so the three arrows are self-explanatory.
- **(3) Recurrence-aware ordering, made legible** — mistake cards are ordered by the
  new selection rank (swing × recurrence likelihood), and each card carries a small
  **"likely to recur" / "one-off" tag** driven by `recurrenceRisk`, so the user can see
  *why* a −1.5 mistake outranks a −3.0 one instead of wondering whether the list is
  broken.
- **(4) Strength estimate in the header** — one line in the header/summary area
  showing `estimatedElo` ("You played this game like a **≈1300**"), with a compact
  **phase mini-row** (opening / middlegame / endgame from `phaseElo`) highlighting the
  weakest phase. `analysisNote` in the footer names both engines and the conditioning
  Elo.
- **(5) Expected-points cost alongside centipawns** — the swing badge (on cards and in
  the feedback panel) shows `expectedPointsLost` next to the centipawn swing, e.g.
  **"−1.42 · −0.21 pts"**, with a tooltip/legend line explaining "pts = expected score
  lost against human opposition at your level."

All new elements render only when their fields are present, so the template keeps
working for the existing pages in `games/` and for any game analyzed without Maia
(e.g. if the install fails in a session — the page then looks exactly as today).

## 3. Process changes (`CLAUDE.md` workflow)

- **Setup** (extends the known-good venv setup):

  ```bash
  apt-get install -y stockfish
  python3 -m venv /tmp/chess-venv && /tmp/chess-venv/bin/pip install chess maia3
  ```

- **Step 2 gains a second pass**: after the Stockfish sweep, run Maia-3 (same
  `SimpleEngine.popen_uci` pattern, `--elo` set to the estimated/stated rating,
  MultiPV ~5) — but only where it's needed, to keep runtime small since Maia inference
  is cheap:
  - an **Elo-estimation sweep** over all user moves (which conditioning band best
    predicts the actual moves, overall and per phase; exclude forced/only-move
    positions from the fit) → `estimatedElo`, `phaseElo`;
  - a **per-mistake query** at the ~10–20 positions where Stockfish flagged a
    meaningful swing → `playedPopularity`, `bestFindability`, `humanBest` (highest
    Maia-probability move whose Stockfish eval is within tolerance — suggested
    default: within 0.5 of best, and not losing), `expectedPointsLost` from the WDL
    delta between the position before and after the played move.
- **Mistake selection** re-ranks by swing × typicality (recurrence likelihood) instead
  of swing alone; moves allowing mate always qualify. `recurrenceRisk` is derived from
  `playedPopularity` (suggested bands: ≥25% high, 10–25% medium, <10% low).
- **Step 3 writing guidance**: takeaways branch on typicality (pattern drill for
  common mistakes vs. blunder-check habit for uncharacteristic slips), and
  explanations reference the human-findable move when the engine best isn't one.
- **Step 6 verification** extends naturally: the existing checks stay
  (`movesSan[ply] === played`, `window.__review` checks via Playwright + the
  pre-installed Chromium), plus: `humanBest`, when present, is legal in the position
  before `ply` and eval-acceptable; percentage fields parse as percentages; the new
  badges/rows/arrow render for a mistake that has the fields and are absent for one
  that doesn't.

## Caveats (state these up front in any implementation)

- Maia-3 is a **predictor, not an evaluator** — Stockfish must remain the ground truth
  for `evalBefore/After/Best`; Maia only ever supplies probabilities and human-WDL.
  Don't blend the two into one number.
- Maia is trained on human-vs-human (Lichess) games; most games in this repo are vs.
  Stockfish levels, whose off-beat play can produce positions slightly out of
  distribution. Probabilities in weird positions deserve a grain of salt, and the
  estimated-Elo fit should exclude forced/only-move positions.
- Maia-3 was released in 2026 (after the assisting model's knowledge cutoff), so
  before wiring it into the workflow, **verify in the sandbox** that
  `pip install maia3` + the Hugging Face checkpoint download actually work through the
  network proxy, and benchmark the 5M vs. 23M model — 23M is likely the sweet spot on
  CPU. If the install fails, the workflow falls back to today's Stockfish-only
  behavior (all new fields omitted).

## Verification

- Prototype first: install Maia-3 and run it against one existing `pgn/` game (the
  2026-07-13 Stockfish-level-3 game is a good testbed) and produce a side-by-side of
  the current page vs. a Maia-augmented one before committing to the schema.
- Template: load a page with the new fields and one without (an existing `games/`
  page) headless via Playwright; assert `window.__review.error` is null on both, the
  new UI elements appear/disappear correctly, the third arrow only draws when
  `humanBestArrow` is present, and clicking mistake cards still jumps the board.
- Pipeline: sanity-check that `playedPopularity` for the user's actual played moves
  averages well above random, and that the best-fit `estimatedElo` is stable (±100)
  across two runs.
- Commit on **`main` directly** (per the user's instruction for this plan), one page
  per analyzed game as usual afterwards.
