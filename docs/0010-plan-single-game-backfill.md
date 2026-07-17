# Single-Game Backfill — regenerate one pre-existing page per request

**Origin**: this was item 5 ("Backfill: regenerate the pre-existing game
pages") of `docs/0009-plan-learning-loop-4-polish.md`. It is split out
here so that backfilling is **one game per request** rather than a single
session that rewrites every old page at once — smaller, verifiable units
of work that can also run **in parallel** across different games.

**Prerequisites — verify before starting**: parts 1–4 of the *faster
learning loop* series are complete and the template is stable:

1. `docs/0005-plan-learning-loop-1-foundation.md` — sidecars, taxonomy, accuracy, drill links
2. `docs/0006-plan-learning-loop-2-practice.md` — retry mode + personal drill deck
3. `docs/0007-plan-learning-loop-3-insight.md` — eval graph, progress dashboard, honest Elo
4. `docs/0009-plan-learning-loop-4-polish.md` — highlights, opening report, trend regen, clocks

Check for: `analysis/*.json` sidecars (one per `pgn/*.txt`),
`drills/index.html` + `tools/build-drills.*`, `reports/progress.html` +
`tools/build-progress.*`, and the eval-graph `evals` field, retry mode, and
polish fields (`highlights`, `openingReport`) in `template.html`. If
anything is missing, run the corresponding earlier plan first. This plan is
the only one allowed to overwrite shipped pages — which is why it runs
after the template has proven stable.

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

## How this plan is invoked

Each time this plan (0010) is mentioned, the user names **one** game to
regenerate — by its `games/*.html` filename, its stamp, or the players.
Regenerate that single game and nothing else. Because each invocation
touches only its own game's files, several invocations may run **in
parallel** in separate sessions to speed the backfill along; keep the work
scoped to the one named game so the parallel runs never contend.

If the user mentions the plan without naming a game, list the pages still
missing the current fields (compare each `games/*.html` GAME block against
what its `analysis/*.json` sidecar supports) and ask which one to
regenerate.

## Scope — regenerating the one named game

All pages generated before the learning-loop series lack the new fields
(accuracy strip, win% rows, tags, drill links, retry, eval graph, and the
part-4 highlights/opening report; the 2026-07-14 page even predates the
Maia fields and per-move arrows). Regenerate the **one requested** page from
its `pgn/*.txt` + `analysis/*.json`:

- Rebuild only that page's GAME block on the current `template.html` with
  all fields the sidecar supports, re-running only what the sidecar lacks
  (e.g. `retry` probes if part 2's backfill didn't cover the game, per-move
  `moveNotes` for a pre-arrows page per `docs/0004-plan-per-move-arrows.md`).
- **Preserve the authored coaching prose verbatim** — titles, subtitles,
  summaries, explanations, takeaways are editorial content; regeneration
  adds data fields around them, it does not rewrite them. Where the page's
  mistake list would change under the new swing×recurrence selection, keep
  the existing mistakes (the prose is tied to them) and only annotate them.
- Run the full step-6 verification (Playwright + python-chess checks in
  `CLAUDE.md`) on the regenerated page before committing it.
- Regenerate the drill deck (`tools/build-drills.py`) and progress
  dashboard (`tools/build-progress.py`) after updating the sidecar, and
  commit them **with** this game's files. They are deterministic and
  read every sidecar, so a run for one game simply reflects that game's
  refreshed data; parallel runs each regenerate them from the sidecars
  present at commit time — a later run subsumes an earlier one, and any
  ordering merges cleanly.
- **One commit for the one game**: its `games/<stamp>.html` +
  `analysis/<stamp>.json` (+ `pgn/<stamp>.txt` if it changed) + the
  regenerated `drills/index.html`, `reports/progress.html`, and the
  `games/index.html` entry if it needs refreshing. Push when the single
  page verifies.

## Out of scope

Everything delivered in parts 1–4 of the series. No new analysis passes; no
template redesign; no index restructuring beyond the existing marked
regions. Regenerating more than the one named game in a single invocation —
each request handles exactly one game.

## Deliverables (per invocation)

| File | Change |
|---|---|
| `games/<stamp>.html` | The one named page regenerated on the current template |
| `analysis/<stamp>.json` | Highlights (and any newly computed fields) added for that game |
| `drills/index.html`, `reports/progress.html` | Regenerated from all sidecars |
| `games/index.html` | Entry refreshed if the page's title/metadata changed |

## Verification (per regenerated page)

- The full `CLAUDE.md` step-6 check passes: replay total, final placement
  vs python-chess, `movesSan[ply] === played`, moveNotes/humanBest rules,
  retry legality, eval-graph and accuracy/tag/win% assertions — run
  `tools/verify-game.py games/<stamp>.html`.
- The authored prose is byte-identical to the old page's — extract and diff
  the text fields (title, subtitle, summary, explanations, takeaways)
  against the pre-regeneration version.
- `games/index.html` entries still resolve to files in `games/`.
- `tools/build-drills.py` and `tools/build-progress.py` remain
  byte-identical when re-run, and their entry counts equal the sidecar
  totals.
- Commit conventions: work on whatever branch the session designates; one
  commit per regenerated game; push when the page verifies.
