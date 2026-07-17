# Implementation log — learning loop part 3: insight

**Date**: 2026-07-17 ·
**Plan**: `docs/0007-plan-learning-loop-3-insight.md` ·
**Branch**: `claude/learning-loop-3-insight-8njixl` (per the session's
instruction; merged to `main` via PR #1, merge commit `b4add05`) ·
**Commits**: eval graph, honest Elo + sidecar recompute, progress
dashboard (one commit each, per the plan's commit conventions)

## What was implemented

1. **Clickable win% eval graph in `template.html`** — an inline-SVG
   sparkline (`#eval-graph`) rendered under the board controls, wired to
   the new optional top-level `GAME.evals` field (one win% number per
   half-move, user's perspective — the whole series or nothing). Features:
   - 50% midline, filled area under the polyline, gold stroke matching the
     house palette;
   - rust `.graph-dot` markers on every mistake ply; clicking one calls the
     same `openMistake(mk)` path as clicking the mistake card — jump,
     `mistake-active`, and (new) respects the practice-first toggle by
     starting a retry instead, which the plan didn't explicitly require but
     "behaves exactly like clicking that mistake's card" implies;
   - a cursor line two-way synced with the replay (`updateGraphCursor()`
     runs at the end of `renderPosition()`); clicking anywhere on the graph
     jumps the replay to the nearest ply;
   - test hooks `window.__review.graphPly()` (current ply while a graph
     exists, else `null`) and `graphClick(ply)`.
   - The template's own placeholder GAME data now carries a real
     Stockfish depth-20 `evals` series for the 7-ply demo game, so
     `template.html` doubles as an all-fields test page (matching the
     convention set in part 1).
   - Old pages (no `evals`) render with no graph and `error === null`,
     unchanged.

2. **Honest Elo estimation** — changed both the CLAUDE.md spec and the
   nine existing sidecars' `eloFit` blocks (`analysis/*.json`):
   - **Fit exclusions**: forced/only-move positions (already excluded in
     part 1) plus positions where `|evalBefore| > 6` pawns (dead-won/lost
     conversion phases), *unless* excluding them would leave a fit with no
     sample at all — then the eval cut is relaxed for that fit only. This
     directly targets the plan's cited failure case (a 35-move forced
     endgame dominating a phase fit).
   - **Mechanical display rule**: `spread` = best band's mean log-prob
     minus the worst band's (nats/move); `flat = spread < 0.15`; `floor =
     best band == 1100`. Display order: `flat` → `"unclear"`, else
     `floor` → `"≤1100"`, else `"≈<band>"`. All three flags
     (`flat`/`floor`/`spread`) now live in the sidecar's `eloFit` block
     alongside `best`/`positions`/`logProbByBand`.
   - **ACPL corroboration**: `estimatedEloNote` gets an approximate
     ACPL-based rating ballpark (six bands, ACPL ≤ 20 → ~2000+ down to
     > 120 → below ~900) as corroboration only, never the headline number.
   - **Documented, not built**: a CLAUDE.md caveat on sub-1100 inference
     (comparing user-move probability against the 1100 band's own median
     predictability) and revisiting Maia-2/3 if the sandbox network policy
     changes.
   - **All nine sidecars recomputed** under the new rule (script run from
     the scratchpad, not committed — same "not a pipeline deliverable"
     precedent as part 1's backfill tooling). Only each file's `eloFit`
     block changed; `plies`, `mistakes`, and `accuracy` were untouched.

3. **Progress dashboard** — `tools/build-progress.py` (new, plain
   python3, no venv/engines — reads only `analysis/*.json`) generates
   `reports/progress.html` from a new `progress-template.html` by
   replacing the marked `const PROGRESS = {…};` block, mirroring the
   `build-drills.py` / `drills-template.html` discipline. Per-game entry:
   `accuracy`, `acpl`, `blunders` (from `moveQuality.blunders`),
   `mistakes` (count), `phases` (per-phase accuracy where present), `elo`
   (display string + `flat`/`floor` + an ACPL-ballpark note, via the same
   honest-display logic as the pipeline spec), and `tags` (each mistake
   counted once under its **first** tag). The template renders:
   - five inline-SVG charts (accuracy, ACPL, blunders-as-bars, estimated
     strength with hollow points for flat/floor fits, per-phase accuracy
     as three overlaid series) with hover tooltips via native SVG
     `<title>`, direct end-labels, and a legend for the phase chart;
   - a tag-recurrence table, one row per taxonomy tag actually seen,
     columns = games (linked to their review pages) sorted by date,
     shaded by count, with a total column.
   - `window.__progress` test hooks (`games()`, `tagColumnSum(i)`,
     `mistakes(i)`, `elo(i)`).
   - Linked from a new entry in the `games/index.html` `TOOLS` region
     (card styled like the existing drill-deck card).

4. **`CLAUDE.md`** — bumped to Version 5: the `evals` field documented in
   step 2c and the GAME data reference; step 2b rewritten for the
   mechanical flat/floor rule and fit exclusions; new step 4d (regenerate
   the dashboard, commit with each game); dashboard entry in the repo
   layout; eval-graph and dashboard verification checklists appended to
   step 6; the `TOOLS` region description and final commit list both
   updated to mention the dashboard.

## Verification results

- **Eval graph** (Playwright, headless Chromium, 13 checks against
  `template.html` + the two pre-existing evals-less pages): `error ===
  null`; graph visible with polyline points == plies + 1; every y-value
  inside the SVG viewBox (equivalently [0,100] win%); the mate-against
  final ply plots at the bottom of the scale; stepping the replay moves
  the cursor and `graphPly()` tracks `getPly()`; `graphClick(ply)` and a
  raw click on the SVG both jump the replay; clicking a mistake dot lands
  on the mistake's ply and sets `mistake-active`; the same dot click
  starts a retry when practice-first is on; the graph stays visible during
  an active retry; both pre-existing pages (2026-07-14, 2026-07-15, no
  `evals`) load with `error === null` and no `#eval-graph` markup at all;
  zero page errors throughout.
- **Elo rule**: a synthetic clearly-peaked fit (`spread=0.4`, not at the
  floor) still yields `"≈1500"`; the 2026-07-15 sidecar — the plan's cited
  misleading case — now computes `flat=true` (spread 0.115) and renders
  `"unclear"` instead of the old `"≈1900"`. Across all nine games, two now
  render `"≤1100"` (floor) and two render `"unclear"` (flat); the
  remaining five keep a confident band. Recompute touched only `eloFit` in
  each sidecar (confirmed via `git diff --stat`).
- **Dashboard**: `tools/build-progress.py` run twice back-to-back produces
  a byte-identical `reports/progress.html` (`md5sum` match); series length
  (9) equals the sidecar count; every one of the 9 game links resolves to
  a file in `games/`; every game's tag-table column sum equals that
  sidecar's `mistakes` array length; loads headless with
  `window.__progress.games() === 9` and no script/console errors (only
  the pre-existing, unrelated Google Fonts fetch failure common to every
  page in this sandbox).
- **Regression check**: re-ran `tools/build-drills.py` after the sidecar
  `eloFit` recompute — output unchanged (41 drills, no backfill triggered,
  since `retry` blocks were untouched); re-ran the full eval-graph
  Playwright suite and an index-page load after adding the dashboard card
  — 11 `.game-card` entries (2 tools + 9 games), zero page errors.
- **Palette**: the dashboard's three phase-series colors
  (`--s-gold #b28a36`, `--s-blue #5e8ecc`, `--s-rust #c1502f`) were run
  through the dataviz skill's `validate_palette.js` against the dark panel
  surface (`#181e27`) — lightness band, chroma floor, CVD separation,
  normal-vision floor, and contrast all PASS. The raw house palette
  (gold/cream/rust) failed the chroma-floor and lightness-band checks for
  a 3-series categorical chart, so the phase chart specifically uses this
  adjusted trio; single-series charts (accuracy, ACPL, blunders, Elo) kept
  the house gold/rust directly since a lone series needs no CVD
  separation.

## Judgment calls / deviations from the plan

- **Flat-fit threshold (0.15 nats/move)**: the plan asked for a threshold
  "picked during implementation and written into CLAUDE.md" — reused
  part 1's already-established value (`docs/logs/…foundation.md` records
  it was chosen because the one self-described "nearly flat" page had
  spread 0.138 while separated fits were ≥ 0.19). Recomputing under the
  new exclusions shifted individual spreads, but the same 0.15 cut still
  splits the nine games into a low cluster (≤ 0.146) and a clearly higher
  one (≥ 0.164) — no evidence the threshold needed to move for this part.
- **`floor` definition**: the plan says "rails at the floor (1100)"; taken
  literally as "the best-fit band equals 1100," not "log-prob for 1100 is
  within some epsilon of the max" — simpler and matches the plan's own
  phrasing plus the worked example in `estimatedEloNote`(`"band fit ≤1100
  (floor)"`).
- **Dashboard chart set**: the plan lists accuracy, ACPL, blunders,
  estimatedElo (with confidence state), per-phase accuracy, and the tag
  table — implemented as five separate small charts plus the table rather
  than one combined view, favoring the existing house pattern of several
  `.chart-card` panels in a grid (matches `.mistake-card`/`.chart-card`
  conventions already used elsewhere) over a denser but more
  library-like combined chart.
- **Graph dot + practice-first interaction**: not explicitly specified by
  the plan ("clicking a dot behaves exactly like clicking that mistake's
  card") — since a mistake card's own click handler already branches on
  practice-first, the graph dot was wired to call the exact same
  `openMistake()` function rather than duplicating the branch, so the two
  can never drift out of sync.
- **eloFit recompute tooling**: as in part 1's sidecar backfill, the
  one-off recompute script lived in the session scratchpad, not the repo —
  the plan's deliverables list only the CLAUDE.md rule change and the
  sidecar diffs, not a standing recompute tool; CLAUDE.md steps 2b/4b
  contain everything needed to reproduce a sidecar's `eloFit` from
  scratch.

## Other notes for later parts

- `reports/progress.html` and `progress-template.html` follow the
  established "generated file vs. hand-edited template" split — do not
  hand-edit the generated dashboard; fix UI in the template and re-run
  `tools/build-progress.py`.
- Part 4 (`docs/0008-plan-learning-loop-4-polish.md`) is expected to
  regenerate/backfill existing `games/*.html` pages; this part
  deliberately left all nine existing pages untouched (no `evals` field
  added retroactively), consistent with the plan's "existing games/*.html
  are not touched" scope note — the eval graph will only appear on pages
  generated from now on until part 4 backfills it.
- **The honest-Elo rule change is retroactive in the sidecars only, not in
  already-generated page HTML.** Checked all nine `games/*.html`: only
  `2026-07-15-21-31-emgosr-vs-maia-800.html` has a Maia-derived
  `estimatedElo` baked into its `GAME` block — `"≈1900"`, the exact
  misleading value the plan cites as this part's motivating example. Its
  sidecar's `eloFit` now correctly says `flat: true` and would display
  `"unclear"`, but the static page itself still shows the old `"≈1900"`
  string until it is regenerated. This is intentional and in scope per the
  plan's explicit exclusion ("existing `games/*.html` are not touched…
  part 4 backfills old pages") — flagging it here so part 4 knows this
  page is the priority backfill target, not just a nice-to-have.
