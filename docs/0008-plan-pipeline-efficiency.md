# Pipeline Efficiency — Consolidate Analysis and Verification Round Trips

**Run this before** `docs/0009-plan-learning-loop-4-polish.md` (part 4 of the
*faster learning loop* series). This plan is not part of that series and
does not add any user-facing field, page section, or GAME schema — it only
changes *how* a Claude Code session executes the existing `CLAUDE.md`
workflow, so it's safe to run ahead of, after, or interleaved with any
learning-loop part. Fresh session, no other context assumed.

## Context — repo essentials (self-contained)

`goossaert/chess-coach` turns uploaded PGN chess games into interactive HTML
coaching pages, one per game, following the step-by-step workflow in
`CLAUDE.md` (the whole file is the spec — read it before touching anything).
In short, per game the workflow currently runs:

- **Step 2** — a Stockfish pass (depth 20, via `python-chess` +
  `/usr/games/stockfish`) over every user move: eval before/after/best,
  best move SAN+UCI.
- **Step 2b** — a Maia rating-band pass (`tools/maia/`, headless-Chromium
  zerofish WASM lc0, bands 1100–1900) for typicality/findability/expected
  score, plus the human-findable-move scan (re-checking candidate moves at
  depth ~18).
- **Step 2c** — win%/accuracy/ACPL/move-quality math, computed in Python
  from the step-2 evals (no extra engine calls).
- **Step 2d** — a `multipv=5` Stockfish probe per selected mistake, to build
  the `retry` object (solutions/acceptable/legal moves).
- **Step 4b** — write the `analysis/<stamp>.json` sidecar with all of the
  above.
- **Step 6** — headless Playwright verification of the generated page
  against `window.__review` hooks (replay correctness, mistake clicks,
  moveNotes/humanBest completeness, retry legality, etc.), plus several
  python-chess sanity re-checks (legality, FEN/placement matching).

Each of these steps is normally driven by the Claude Code session issuing
one or more Bash tool calls, reading back the output, and reasoning about
the next step. That back-and-forth is the thing this plan reduces — **not**
the underlying engine work, depths, bands, or checks themselves, all of
which must stay byte-for-byte the same in substance so analysis quality is
unaffected.

**Design principle (non-negotiable):** this plan changes *tooling*, never
*analysis parameters*. Same Stockfish depth (20, and 18 for the
human-findable re-check and retry probes), same Maia bands (1100–1900),
same accuracy/Elo formulas, same Playwright assertions. If any consolidation
would require cutting a corner to save tokens (lower depth, fewer bands,
skipped checks), do not make that change — flag it instead and leave the
step as-is.

## Goal

Reduce wall-clock time and tokens spent per game analysis by cutting the
number of tool round trips and the volume of tool output that flows back
into the model's context, without changing any computed number, any
generated field, or any verification check's pass/fail behavior.

## Scope of this part

### 1. One consolidated analysis script (steps 2 + 2b + 2c + 2d)

Today these four steps are naturally invoked as separate Bash calls (and,
within step 2, often as a per-move loop of engine calls with intermediate
output read back into context). Replace this with a **single Python script**
that:

- takes a PGN (or parsed move list + user color) as input,
- runs the full per-ply loop once: Stockfish eval before/after/best,
  win%, then the Maia job construction,
- shells out once to the existing `tools/maia/query.cjs` batch harness
  (already a single call per game — keep it that way, do not split it
  per-position),
- computes accuracy/ACPL/move-quality/Elo-fit from the same in-memory
  per-ply data (no re-reading anything from disk),
- runs the mistake-selection weighting (swing × recurrence) and the
  step-2d `multipv=5` retry probes for the selected mistakes,
- and **prints exactly one JSON document** to stdout containing everything
  steps 2/2b/2c/2d/4b need: the per-ply series, the accuracy block, the
  Elo fit, and the per-candidate-mistake data (including `retry`).

The model then makes one Bash call, reads one JSON blob, and has everything
it needs to write the coaching prose (step 3), the GAME block (step 4), and
the sidecar (step 4b) — instead of piecing results together from several
separate tool outputs across the course of the analysis.

Suppress verbose per-move progress printing from this script (no
`print(f"ply {i}: ...")` loops) — stdout should be the final JSON only,
plus a short stderr progress indicator if useful for a human watching a
long-running call (stderr doesn't count against the model's context the
way stdout captured by the tool result does... actually tool output
captures both streams, so keep even stderr minimal: at most one line per
major phase, e.g. "stockfish pass done", "maia query done").

Land the script at `tools/analyze-game.py` (new). It wraps, rather than
replaces, the existing pieces — it still calls into `tools/maia/query.cjs`
as a subprocess, still uses `python-chess` + `/usr/games/stockfish`, still
applies the exact formulas already specified in `CLAUDE.md` steps 2b/2c/2d.
Do not reimplement those formulas differently "for speed" — copy them
verbatim from the current workflow description.

### 2. One consolidated verification script (step 6)

Today's step 6 is a checklist of many separate assertions, naturally run as
several Playwright `page.evaluate` calls plus several separate python-chess
re-checks, each a separate tool round trip with its own output. Replace
with a **single script** (`tools/verify-game.py` or `.mjs`, new — pick
whichever integrates more simply with the existing headless-Chromium
Playwright setup already used for Maia and confirm it can drive Playwright
directly rather than only serving static files) that:

- loads the generated page headless once,
- runs every `window.__review` check from `CLAUDE.md` step 6 in sequence
  inside that one page load (error banner, ply/placement, mistake clicks,
  moveNotes/humanBest completeness and legality, Maia field presence,
  retry legality, eval-graph checks when `evals` is present),
- cross-checks against python-chess (legality, FEN/placement, `tags`
  vocabulary) in the same script,
- and prints **one summary**: a short list of `PASS`/`FAIL` lines (or,
  ideally, nothing but a single "all checks passed" line when everything
  is green, with full detail only for whatever fails).

Every individual assertion currently listed in `CLAUDE.md` step 6 must
still run — this is a packaging change, not a coverage cut. If a page
fails, the script should print enough detail (which check, which ply) to
debug without re-running things piecemeal, but a healthy page should
produce minimal output.

### 3. Suppress incidental noise everywhere else

Audit the remaining workflow steps for tool calls whose output is mostly
noise relative to what the model needs next, and quiet them down — this is
lower-effort cleanup alongside items 1–2, not a new phase:

- `tools/maia/setup.sh` and `node tools/maia/serve.mjs` — check whether
  their normal-path output can be shortened (keep errors verbose; quiet
  the happy path).
- `tools/build-drills.py` / `tools/build-progress.py` — these already run
  once per game and are meant to be near-silent on success; confirm they
  don't print a per-sidecar line for every game in the repo (that scales
  with total games analyzed, not with the one game being added, and will
  get noisier every session going forward).
- Any place the existing workflow reads a full file (e.g. `template.html`,
  an example page) purely for the model to re-derive something it was
  already told in `CLAUDE.md` — prefer pointing at the specific
  line range instead of a full-file read, where practical.

## Out of scope

No changes to Stockfish depth, Maia bands, any formula (win%, accuracy,
Elo fit, ACPL), the mistake-selection weighting, the GAME/sidecar schemas,
`template.html` markup/CSS/scripts, or any verification *assertion*'s
meaning — only how many tool calls and how much printed output it takes to
run them. No changes to `drills-template.html` or `progress-template.html`
UI. No parallelization advice belongs here either — running multiple games
in parallel sessions is a session-orchestration choice the user makes
separately, not a pipeline change.

## Deliverables

| File | Change |
|---|---|
| `tools/analyze-game.py` (new) | Consolidates steps 2/2b/2c/2d into one script, one JSON stdout |
| `tools/verify-game.py` or `.mjs` (new) | Consolidates step 6 into one script, PASS/FAIL summary |
| `tools/build-drills.py`, `tools/build-progress.py` | Quieted if currently noisy on the happy path (no logic change) |
| `tools/maia/setup.sh`, `tools/maia/serve.mjs` | Quieted happy-path output only |
| `CLAUDE.md` | Steps 2/2b/2c/2d point at `tools/analyze-game.py`; step 6 points at the new verify script; note that the underlying checks/formulas are unchanged and still normatively described inline |

## Verification

- Run the new `tools/analyze-game.py` against an already-analyzed game's
  saved `pgn/*.txt` and diff its JSON output's numbers (evals, win%,
  accuracy, ACPL, Elo fit, retry solutions/acceptable/legal) against that
  game's existing `analysis/*.json` — they must match (modulo formatting),
  proving the consolidation didn't change any computed value.
- Run the new `tools/verify-game.py` against three existing pages spanning
  different versions (a Stockfish-only page, a Maia page without retry, a
  current-template page with retry + eval graph) and confirm it reports
  the same pass/fail verdict as manually walking the `CLAUDE.md` step-6
  checklist would — every check fires on the page type it applies to and
  is silently skipped (not falsely failed) on pages that predate that
  field.
- Deliberately break one thing per script (e.g. corrupt a `moveNotes`
  entry's `bestArrow`; feed an off-by-one FEN) and confirm the verify
  script's output still identifies the specific failing check, not just
  "something failed."
- Time/output comparison: on one real game, count Bash/tool round trips
  and approximate output size for the old step-by-step approach vs. the
  new consolidated scripts, and note the reduction in this plan's
  implementation log (`docs/logs/`) — this is the evidence the effort
  paid off.
- Commit conventions: work directly on `main` (per this session's explicit
  instruction — do not create a feature branch), one commit for the new
  tools, one for `CLAUDE.md`'s updated step references; push when done.
