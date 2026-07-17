# Implementation log — learning loop part 2: active practice

**Date**: 2026-07-17 ·
**Plan**: `docs/0006-plan-learning-loop-2-practice.md` ·
**Branch**: `main` (per the session's instruction to work directly on main;
the part-1 branch `claude/learning-loop-1-foundation-9f7h8v` was merged in
first — it is the plan's hard prerequisite and was complete but unmerged) ·
**Commits**: template retry mode, drill generator + deck + sidecar backfill,
CLAUDE.md (one each, per the plan's commit conventions)

## What was implemented

1. **Retry mode in `template.html`** — every mistake that carries the new
   `retry` field gets a "↻ retry" chip on its card: the board jumps to the
   position before the mistake with arrows, legend, and eval compare hidden,
   and takes click-to-move input (origin square then destination, legal
   targets dotted, promotions default to queen). Grading is instant and
   engine-free: `solutions` (engine best + humanBest) → solved;
   `acceptable` (within 0.5 pawns of best) → "also fine — the cleanest
   was …"; any other legal move → one more try, then reveal; illegal
   clicks are ignored. The resolved state re-renders the full mistake
   feedback with a `.retry-result` banner. Test hooks:
   `window.__review.retryStart(i)` / `retryPlay(uci)` / `retryState()`.
   Old pages carry no `retry` field and render exactly as before.

2. **`retry` backfill in all 9 sidecars** (41 mistakes) — computed by
   `tools/build-drills.py`: `legal` from python-chess, `acceptable` from a
   Stockfish depth-18 `multipv=5` probe (evals clamped to ±10 pawns, mates
   through `mate_score=100000`), minus the solutions and the played move
   (repeating the game mistake must never grade as "also fine"). Written
   back with the same `json.dumps(indent=1, ensure_ascii=False)`
   serialization part 1 used, so the files stay byte-stable.

3. **The drill deck** — `drills-template.html` (committed template) +
   `tools/build-drills.py` (generator) + `drills/index.html` (generated,
   41 drills). The generator replaces only the marked `const DRILLS = […];`
   block and is deterministic (two consecutive runs byte-identical). Front
   end: house style, trimmed copy of the board renderer with the same
   click-to-move grading, Leitner boxes 1–4 in `localStorage`
   (`chess-drills-v1`, keyed `<stamp>:<ply>`; fail → box 1 due now;
   first-attempt solve → next box, due in 1/3/7 days), due/streak/deck
   counters, tag filter, per-drill link back to the source game, and a
   "practice ahead" mode when nothing is due. All storage access is
   try/catch-wrapped (iOS-Safari-safe), no external JS.

4. **Active-recall features beyond the plan's letter** (requested for this
   part): the plan's retry mode *is* retrieval practice; on top of it —
   - **practice first** toggle on game pages (persisted): clicking a
     mistake card starts a retry instead of revealing the coaching, so
     every mistake is attempted before it is read (pre-testing);
   - **recall the lesson** stage in the drill deck: after grading, the
     takeaway lesson stays hidden behind a "say it out loud, then reveal"
     step — retrieval of the verbal heuristic, not just the move;
   - **interleaving**: the due queue is round-robined across source games
     so the same game's (usually same-theme) drills don't run
     back-to-back;
   - failed drills are **re-queued within the session** (immediate retrieval
     after feedback) on top of their box-1 reset.

5. **`games/index.html`** — new `TOOLS` / `END TOOLS` marked region above
   the game list with one drill-deck card; game-list markup untouched.

6. **`CLAUDE.md`** — bumped to Version 4: new step 2d (retry precompute),
   `retry` in the GAME reference and sidecar schema, new step 4c
   (regenerate the deck and commit it with each game), the TOOLS region in
   step 5, and the retry/deck verification list in step 6.

## Verification results

57 Playwright checks + 41-mistake data sweep, all green at final state:

- **Retry data**: for every mistake, `solutions ⊆ legal`,
  `acceptable ⊆ legal`, disjoint, every UCI legal in `retry.fen`,
  `retry.fen == fenBefore`, `bestUci ∈ solutions`, played move in neither
  list; sidecars still round-trip byte-identically.
- **Retry UI** (headless Chromium, real synthetic clicks incl. the flipped
  board's coordinate mapping): solve / acceptable / wrong-twice / give-up
  paths, illegal input ignored, arrows + legend + compare hidden during
  input and restored on reveal, navigation cancels, practice-first starts
  retries from cards and persists across reloads. Old pages (2026-07-14,
  2026-07-15) load with `__review.error === null` and show no retry UI.
- **Drill deck**: 41 entries = total sidecar mistakes; every source link
  resolves; solve → box 2 due tomorrow, survives reload; fail → box 1 due
  today, re-queued, streak reset; tag filter leaves only matching drills;
  lesson hidden until the recall button; generator byte-deterministic; no
  script errors headless (the only console noise is the Google Fonts
  fetches, blocked in this sandbox for every page in the repo).

## Judgment calls

- `acceptable` excludes the played move even when the probe ranks it inside
  the 0.5-pawn window — grading the original mistake "also fine" would
  defeat the drill. The plan doesn't state this; it seemed clearly intended.
- "Solved" for Leitner purposes means **first-attempt** solved/acceptable;
  needing the second try or the reveal counts as a miss (box 1). The page's
  retry banner still celebrates a second-try solve, it just tells the user
  it will come back soon.
- A `.legend-item[hidden]` display rule was needed in the drills template:
  the flexbox item rule otherwise overrides the UA `[hidden]` style and the
  "human-findable" legend leaked onto single-solution drills (found by
  screenshot inspection, covered by a check now).
