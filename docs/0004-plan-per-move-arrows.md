# Per-Move Arrows on Every User Move — Plan

**Status: implemented** (template.html, CLAUDE.md workflow, and the 2026-07-15
game page regenerated). This document records the context, the design decisions,
and the details a fresh session needs to keep the behavior intact.

## Context — what the pages showed before

Generated review pages (version 2, per `docs/0003-plan-maia-engine.md`) drew
board arrows — rust for the move played, gold for the engine's pick, cream for
the Maia human-findable move — **only on the 3–6 mistake positions**. Stepping
through any other move of the game showed a bare board: no arrows, no legend,
no record of what the engine or a human peer would have played there. Arrows
that happened to coincide (played == engine's pick) were drawn stacked on top
of each other, so only the topmost color was visible.

### The user's requests (two iterations)

1. > The moves and arrows for the move that was played, the engine's pick, and
   > the human findable are only displayed for the mistakes, and not for all
   > the other moves. Modify the workflow so that all three will be shown for
   > every single move that is made by the user. And if arrows are superimposed
   > (e.g. the played move is also the engine's pick or the human findable),
   > show them side by side — reduce the arrow width if needed — instead of on
   > top of each other. Distinct arrows keep the current width.

2. After the first implementation kept the version-2 rule of only emitting
   `humanBest` when the engine's best was near-unfindable (< 10% at the band):
   > The human-findable arrows are missing for many moves, for example moves
   > 1 through 3. Fix it in the workflow so that they never go missing again.

   The lesson: on these pages the human-findable move is **not an occasional
   alternative — it is a mandatory third annotation** on every user move.

## Design

### 1. `moveNotes` — per-move annotations in the GAME data

A new optional top-level GAME field carries one entry per user move:

```js
moveNotes: [
  { ply: 4, best: "Nf3", bestArrow: ["g1","f3"],
    humanBest: "Nc3", humanBestArrow: ["b1","c3"] },
  …
],
```

- `ply` uses the same 0-based convention as `mistakes`.
- `best`/`bestArrow` come from Stockfish, so they belong on **Stockfish-only
  pages too**; only the `humanBest` fields depend on Maia.
- `humanBest`/`humanBestArrow` are **required on every entry of a Maia page**
  (see rule 3 below) and omitted only on Stockfish-only pages.
- **The played arrow is not stored.** The template derives it from its own SAN
  replay (`positions[ply+1].last`), so it can never misalign with the data.
- Plies covered by a `mistakes` entry may be omitted; the template merges both
  sources with mistakes taking precedence (`annoByPly`: notes first, then
  mistakes overwrite).

Old pages (each ships its own template copy) and Stockfish-only data render
unchanged — every new field is optional at the template level; "required" is a
data-generation rule, not a rendering precondition.

### 2. Side-by-side rendering for coinciding arrows

`template.html`'s `drawArrow` gained `scale` and `offset` parameters, and a new
`drawArrowSet(layer, [{from,to,color},…])` groups arrows by their **exact
from→to squares**:

- group of 1 → full size (scale 1, stroke-width 9) — unchanged look;
- group of 2 → scale 0.55 each; group of 3 → scale 0.4 each;
- within a group, each arrow is shifted perpendicular to its direction by
  `(k − (n−1)/2) × headWidth×scale`, so the scaled heads sit edge to edge —
  side by side, never stacked. Shaft width and head size scale together.

Arrows on distinct squares keep the full width even when they cross or share
one endpoint — only exact duplicates are thinned (per the user: partial
overlaps looked fine at full width).

### 3. The human-findable move always exists — mandatory emission

Old rule (v2): only when `bestFindability` < 10%, find the most popular move
within 0.5 of best *and not losing*; emit only if it differed from best. This
left the cream arrow missing on most moves.

New rule: for **every** position where the user is to move, scan the fit
band's Maia moves by **descending probability**; the human-findable move is
the first whose Stockfish eval (re-check at depth ~18, evals clamped to
±10 pawns for the comparison; skip the re-check when the candidate IS the
engine's best) stays **within 0.5 of the engine's best**. The engine's best
always qualifies, so the move **always exists** — often it simply is the
engine's pick, and the gold and cream arrows render side by side.

- `humanBest` + `humanBestArrow` (plus `humanBestFindability` on mistakes) are
  emitted on **every** mistake and every `moveNotes` entry of a Maia page,
  even when equal to `best` or to the played move. A missing cream arrow on a
  user move is a data bug, not a display choice.
- The mistake find-row **text** cites `humanBest` only when it differs from
  `best` (template: `mk.humanBest && mk.humanBest !== mk.best`) so identical
  values don't produce redundant prose — but the arrow is always drawn.
- Never recommend an engine-only move as the lesson when a human-findable one
  keeps the eval.

### 4. Legend shows the actual moves

The board legend (previously static labels, mistakes only) is now rebuilt per
position and shows the move names: `played Nf3 · engine's pick c4 ·
human-findable Nf3`. It is visible on every annotated (user-move) position and
hidden on opponent moves and the start/final positions. The `legend-human`
item shows iff the position's annotation has `humanBestArrow`.

## Template internals (for maintenance)

- `sqName(i)` — inverse of `sqIndex`, used to derive the played arrow from the
  replay's `{from,to}` square indices.
- `annoByPly` — Map built from `GAME.moveNotes` then `GAME.mistakes`; the
  renderer reads `annoByPly.get(current)` (position *before* ply `current`).
- `window.__review.noteAt(ply)` — test hook exposing the merged annotation,
  used by the verification pass.

## Workflow changes (CLAUDE.md)

- Step 2 (Stockfish): keep the best move (SAN + UCI) for **every** user move,
  not just mistakes — it feeds `moveNotes`.
- Step 2b (Maia) now computes **four** things; item 3 is the always-exists
  human-findable rule above, item 4 assembles the `moveNotes` entries.
- Step 6 (verify) additions, all enforced via Playwright + python-chess:
  - every user ply appears in `moveNotes` or `mistakes`
    (`window.__review.noteAt(ply)` non-null);
  - every note's `best`/`humanBest` is legal in the position before its ply
    and the arrows match the moves' UCI;
  - stepping onto any user-move position shows the legend and the arrows;
    coinciding arrows render as thinner, offset, non-stacked `.arrow` elements;
    opponent-move positions show neither;
  - on a Maia page, the cream arrow + "human-findable" legend item are visible
    on **every** user-move position, without exception.

## Applied to the 2026-07-15 game (emgosr vs Maia 800)

Regenerated `games/2026-07-15-21-31-emgosr-vs-maia-800.html` on the updated
template: Stockfish depth 20 over all 53 White moves, Maia queried at the
page's fit band (≈1900), depth-18 re-checks for the human-findable scan.
Result: 49 `moveNotes` entries + the 4 existing mistakes, every one carrying
`humanBest`; 40 positions render coinciding arrows side by side, 13 show three
distinct full-width arrows. Coaching content was left untouched. One notable
by-product: at the move-25 mistake the scan surfaced 25.Be7 (≈2.4% findability)
as an equal save, three times more findable than the authored engine pick
25.Ba3 (0.8%) — the cream arrow shows it.

## Pitfalls learned

- **Don't gate the cream arrow on a findability threshold.** Any "only when"
  rule reads as "missing" to the user; compute the human-findable move
  unconditionally and let coincidence render side by side.
- **Derive the played arrow, never store it** — stored copies can drift from
  the replay.
- Clamp evals (±10 pawns, mates mapped through `mate_score`) before applying
  the 0.5 tolerance so dead-lost/dead-won endgame positions still yield a
  sensible most-human candidate instead of failing every comparison.
- ESM `node` scripts do not see `NODE_PATH`; use `.cjs` + `require` for
  Playwright checks (as `tools/maia/query.cjs` already does).
