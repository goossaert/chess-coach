# chess-coach

**Version 4**

This repository turns chess games into interactive coaching pages. When the user
uploads a game and asks for feedback, analyze it and generate one HTML review page
per game in `games/`, built from `template.html`.

Version 2 (per `docs/0003-plan-maia-engine.md`) adds a **human-model pass**: every
game is checked against Stockfish for the truth of each position *and* against a
Maia rating-band model for what humans at the user's level actually play. This
yields per-mistake typicality and findability percentages, a human-findable
alternative when the engine's best move is one no human would see, mistake
selection weighted by recurrence, an estimated playing strength (overall and per
phase), and eval swings expressed as expected score against human opposition.
Pages generated under version 1 remain valid — every new field is optional.

Version 3 (per `docs/0005-plan-learning-loop-1-foundation.md`, part 1 of the
faster-learning-loop series) adds the **learning-loop foundation**: a
machine-readable analysis sidecar per game in `analysis/` (step 4b), a
controlled mistake taxonomy (`tags`), Lichess-style accuracy / ACPL /
move-quality numbers (step 2c), win-probability framing on every mistake
(`winBefore`/`winAfter`), and curated practice links per mistake
(`drillLinks`, from `tools/drill-links.json`). As before, every new GAME
field is optional — pages generated under versions 1 and 2 remain valid.

Version 4 (per `docs/0006-plan-learning-loop-2-practice.md`, part 2 of the
series) turns review into **active practice**: every mistake carries a
precomputed `retry` object so the page can grade the user's own attempt at
the position (step 2d, retry mode), and all mistakes ever analyzed aggregate
into a standing spaced-repetition **drill deck** at `drills/index.html`
(step 4c, `tools/build-drills.py`). The design leans on active-recall
principles throughout: retrieval before re-reading (retry mode and the
"practice first" toggle), recall of the verbal lesson before it is shown
(the drill deck's "recall the lesson" stage), spaced repetition (Leitner
boxes), and interleaving (due drills are mixed across games). Every new
field remains optional — pages generated under versions 1–3 stay valid and
show no retry UI.

## Trigger

The user uploads or pastes a chess game in **PGN** format (they may call it "PNG" —
they mean PGN) and asks for feedback, analysis, or a review of their moves.
One uploaded game = one generated page. Multiple games = one page each.

## Workflow

### 1. Parse the PGN

Extract the headers (`White`, `Black`, `Result`, `Date`, `Event`, `Opening`/ECO) and
the full SAN move list (strip comments, variations, NAGs, and the result token).

Determine which color the **user** played. Use what they say, or their name in the
headers. If it cannot be inferred, ask before analyzing — every evaluation on the
page is from the user's perspective.

### 2. Analyze with an engine

Prefer real engine analysis. Setup that is known to work in this environment
(system `pip install chess` fails with a setuptools error — use a venv):

```bash
apt-get install -y stockfish            # binary lands at /usr/games/stockfish
python3 -m venv /tmp/chess-venv && /tmp/chess-venv/bin/pip install chess
```

For each position where the user is to move, get (depth 20 is a good default):

- eval **before** the move (from the user's perspective: `score.pov(user_color)`),
- the engine's **best move** and the eval after playing it,
- the eval **after** the move actually played,
- the **swing** = eval_after − eval_before (negative = the move hurt the user).

Keep the best move (SAN + UCI) for **every** user move, not just the mistakes:
it feeds the `moveNotes` array, which puts the played/engine's-pick arrows on the
board for every move the user made (the played arrow is derived in-page from the
replay, so a note only carries the engine's pick and the optional human-findable
fields). On a Stockfish-only page, still emit `moveNotes` with `best`/`bestArrow`
— only the human-findable fields depend on Maia.

Reference loop with `python-chess`:

```python
import chess, chess.engine
engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
board = chess.Board()
for san in moves:
    if board.turn == user_color:
        info = engine.analyse(board, chess.engine.Limit(depth=20))
        before, best = info["score"].pov(user_color), info["pv"][0]
        played = board.parse_san(san)          # .uci() gives arrow squares
        board.push_san(san)
        after = engine.analyse(board, chess.engine.Limit(depth=20))["score"].pov(user_color)
    else:
        board.push_san(san)
engine.quit()
```

If no engine can be installed, analyze by judgment, clearly mark evaluations as
estimates in `analysisNote`, and say so to the user.

### 2b. Human-model pass (Maia)

Stockfish says what is true; Maia says what a human at a given rating actually
plays. Run this second pass whenever possible — it feeds the typicality badges,
findability rows, recurrence tags, strength estimate, and expected-points numbers
on the page. Maia is a **move predictor, not an evaluator**: Stockfish remains the
only source for `evalBefore/After/Best`; Maia only ever supplies probabilities and
human-outcome expected scores. Never blend the two into one number.

**Setup — known to work in this environment** (the plan's preferred
`pip install maia3` does NOT work here: PyPI returns no distribution through the
proxy, and the Maia-2/3 checkpoints on Hugging Face/Google Drive are blocked —
verified 2026-07-15. The original Maia-1 rating-band networks run via the
zerofish WASM lc0 in headless Chromium instead; the harness is committed in
`tools/maia/`):

```bash
tools/maia/setup.sh                                  # zerofish engine + Maia-1 weights (both gitignored)
node tools/maia/serve.mjs &                          # COOP/COEP static server, port 8123
NODE_PATH=/opt/node22/lib/node_modules node tools/maia/query.cjs job.json > maia.json
```

`job.json` is `{ "bands": [1100, …, 1900], "positions": ["<FEN>", …] }`; the
output maps each band to, per FEN, `moves` (UCI → percent of humans in that band
playing it) and `value` (expected score 0–1 for the **side to move** against human
opposition at that band). Generate the FENs with python-chess while replaying the
PGN. Bands run 1100–1900 in steps of 100 — there is nothing below 1100.

Compute four things:

1. **Estimated strength** — for every position where the user is to move, get
   the probability each band assigns to the move actually played. **Exclude
   low-information positions from the fit**: forced/only-move positions, and
   positions where |eval| > 6 pawns (dead-won/dead-lost conversion phases say
   nothing about strength) — unless that exclusion would leave a fit (the game
   fit, or a phase fit) with no sample at all, in which case relax the eval
   cut for that fit. The best-fit band maximizes the mean log-probability
   (floor tiny probabilities at 0.1% so one weird move can't dominate).

   **Honest display rule (mechanical — the pipeline decides, not editorial
   judgment).** Compute `spread` = best band's mean log-prob − worst band's,
   in nats per move, and set two flags: `flat` = spread < 0.15, `floor` =
   best band is 1100 (the bottom of the Maia-1 range — there is nothing
   below it). Then:

   - `flat` → `estimatedElo: "unclear"` — the data doesn't distinguish the
     bands, so never print a confident-looking middle number;
   - else `floor` → `estimatedElo: "≤1100"` — the fit railed at the bottom
     of the measurable range, so the true strength may be anywhere at or
     below it;
   - else → `estimatedElo: "≈<band>"` as before.

   Record `flat`, `floor`, and `spread` in the sidecar's `eloFit` block.
   In `estimatedEloNote`, add an approximate corroborating signal from the
   game's ACPL (rough rapid-pool ballparks from published Lichess-data
   regressions — corroboration only, never the headline number):
   ACPL ≤ 20 → ~2000+, 20–35 → ~1700–2000, 35–55 → ~1400–1700,
   55–85 → ~1100–1400, 85–120 → ~900–1100, > 120 → below ~900.
   Example note: "band fit ≤1100 (floor); ACPL 78 is typical of ~900–1100
   rapid — two weak signals agreeing beat one flat fit."

   Repeat per phase for `phaseElo` (opening ≈ first 10 full moves, endgame
   from when queens are off or few pieces remain, middlegame between; include
   the sample size, e.g. "≈1300 · 43 moves", and set `weakestPhase`), applying
   the same exclusions and the same flat/floor display rule per phase
   ("unclear · 12 moves" beats a confident number a dead-won 35-move endgame
   produced). Small per-phase samples are normal — the ≈ carries the
   uncertainty.
2. **Per-mistake numbers**, at the best-fit band, for the 10–20 positions where
   Stockfish flagged a meaningful swing: `playedPopularity` = probability of the
   played move; `bestFindability` = probability of the engine's best move;
   `expectedPointsLost` = (expected score after the best move) − (expected score
   after the played move), both from the **user's** perspective — the after
   positions have the opponent to move, so use `1 − value`. Display as a signed
   number ("−0.21"); when it rounds to ±0.00 (typical in already-decided
   positions), **omit the field** — the win% row from step 2c tells that story,
   and a printed "±0.00" is a shrug, not information.
3. **The human-findable move** — for **every** position where the user is to
   move: scanning the fit band's moves by descending probability, the first one
   whose Stockfish eval (re-check at depth ~18; skip the re-check when the
   candidate IS the engine's best) stays within 0.5 of best. The engine's best
   always qualifies, so this move **always exists** — often it simply is the
   engine's pick, and then the two arrows render side by side on the page.
   Emit `humanBest` + `humanBestArrow` (plus `humanBestFindability` on
   mistakes) on **every** mistake and every `moveNotes` entry of a Maia page —
   never omit them, not even when `humanBest` equals `best` or the played move;
   a missing cream arrow on a user move is a data bug, not a display choice.
   (The find-row text only highlights `humanBest` when it differs from `best`.)
   Never recommend an engine-only move as the lesson when a human-findable one
   keeps the eval.
4. **Per-move notes** — finish the `moveNotes` entries started in step 2 with
   item 3's result: each entry is `{ ply, best, bestArrow, humanBest,
   humanBestArrow }`, all fields present. Skip plies covered by a `mistakes`
   entry — the template lets mistakes take precedence — but those carry the
   same (mandatory) `humanBest` fields.

**Mistake selection** — rank by **swing × recurrence likelihood** instead of raw
swing: weight each candidate's centipawn loss by `playedPopularity` (floored at
~5% so rare blunders still register). A −1.5 mistake that 35% of the user's level
repeats outranks a −3.0 one-off. A move that allows mate always qualifies, first.
Select 3–6 mistakes; prefer instructive moments over near-duplicates. Derive
`recurrenceRisk` from `playedPopularity`: ≥25% high, 10–25% medium, <10% low.

**Caveats**: most games in `pgn/` are against engines, whose off-beat play can
push positions outside Maia's human-vs-human training data — take probabilities
in weird positions with a grain of salt, and keep forced positions out of the Elo
fit. Percentages in the first ~5 moves are approximate too. The Elo fit can
never say less than "≤1100" because 1100 is the lowest Maia-1 band; a
long-term option (documented here, deliberately not built) is sub-1100
inference by measuring how much *less* probable the user's moves are than
the 1100 band's own median predictability, and Maia-2/3 (with sub-1100
coverage) is worth revisiting if the sandbox network policy ever changes. Name the model and
conditioning band in `analysisNote` (e.g. "human model: Maia rating-band networks
(lc0 via zerofish WASM), conditioned at ≈1300; Maia-3 unreachable from this
sandbox, Maia-1 bands stand in").

**Fallback**: if the Maia setup fails (network policy can change), do the
Stockfish-only analysis and omit every Maia field — the template then renders
exactly as version 1. Say so in `analysisNote` and to the user.

### 2c. Accuracy, win probability, and move quality (Lichess-style)

Computed from the Stockfish pass alone — no new engine work, so these numbers
belong on **every** page, including engine games and Maia-less pages. Formulas
(source: lichess.org/page/accuracy and the lichess-org/lila repository):

- **Win probability**: `win% = 50 + 50 · (2 / (1 + exp(−0.00368208 · cp)) − 1)`,
  centipawns from the **user's** perspective, clamped to ±1000 (map mate scores
  through a large mate score first, e.g. python-chess
  `score.score(mate_score=100000)`, then clamp). Sanity anchors: cp 0 → 50%,
  ±100 → ≈59%/41%, the clamp caps everything at ≈97.5%/2.5%.
- **Move classification** by win% drop (win% before − win% after the user's
  move): **inaccuracy** ≥ 10, **mistake** ≥ 20, **blunder** ≥ 30 percentage
  points; count each move once, at its worst label. This is the `moveQuality`
  tally (`?!` / `?` / `??`).
- **Per-move accuracy**:
  `103.1668 · exp(−0.04354 · (win%_before − win%_after)) − 3.1669`,
  clamped to [0, 100] (a move that gains win% counts as 100).
- **Game accuracy**: aggregate as Lichess does — the mean of a
  volatility-weighted mean (weights = stdev of the win% sequence over a sliding
  window of `clamp(plies/10, 2, 8)` positions, clamped to [0.5, 12]) and the
  harmonic mean of the per-move accuracies. A plain mean-of-(weighted, harmonic)
  is an acceptable approximation — note which was used in `analysisNote`.
- **ACPL**: average centipawn loss vs. the engine's best over the user's moves,
  each loss clamped to [0, 1000].
- Compute all of it **per phase** too, reusing the phase boundaries defined for
  `phaseElo` (opening ≈ first 10 full moves, endgame from queens off / few
  pieces, middlegame between).

This feeds the optional GAME fields `accuracy`, `acpl`, `moveQuality`,
`phaseAccuracy` (stat strip + phase chips in the header) and the per-mistake
`winBefore`/`winAfter` (the "your winning chances: 92% → 45%" row in the
feedback panel).

Also emit the full per-ply series as the GAME `evals` field — one win%
number per half-move (after that ply, user's perspective, the same numbers
as the sidecar's `winAfter`). It powers the clickable eval graph under the
board: the whole series or nothing (the template only renders the graph
when `evals.length` equals the ply count).

### 2d. Retry grading (precomputed — the page stays engine-free)

For each **selected** mistake, run one extra Stockfish probe with
`multipv=5` (depth 18 is fine; seconds of extra runtime) on the position
before the mistake, and build the per-mistake `retry` object that powers
retry mode on the page and the drill deck:

- `solutions` — the engine best + `humanBest` UCIs, deduped;
- `acceptable` — the probed moves whose eval stays within **0.5 pawns** of
  best, minus the solutions and the move actually played (evals clamped to
  ±10 pawns before comparing, mates through `mate_score` — the same clamping
  the human-findable scan uses);
- `legal` — the full legal-move list from python-chess, sorted;
- `fen` — the position before the mistake (redundant safety).

Emit it as the mistake's `retry` GAME field **and** store the identical
object in the sidecar mistake entry (step 4b) so the drill deck can reuse it
without re-running engines. `tools/build-drills.py` computes the same thing
for old sidecars that predate the field, so if a run must skip this step the
deck generator will backfill it later.

### 3. Write the coaching content

For each selected mistake, write:

- `title` — a one-line, memorable diagnosis ("Started a pawn rush with the king still on e8").
- `explanation` — one concrete paragraph in the tone of the existing pages: name the
  squares, the threat that was missed, why the engine's move works. Speak to the user
  ("you"), not about "Black".
- `takeaways` — 1–3 items, each `{ lesson, detail }`:
  - `lesson`: a short imperative heuristic the user can recall at the board
    ("Don't push pawns in front of an uncastled king.").
  - `detail`: how to apply or practice it in future games (a habit, a checklist step, a drill).
- arrows: `playedArrow` and `bestArrow` as `["from","to"]` square names (take them
  from the moves' UCI, e.g. `g8f6` → `["g8","f6"]`).
- `tags` — 1–3 tags from the **mistake taxonomy** below. You are already
  diagnosing the mechanism while writing the explanation; the tag records that
  diagnosis in a form that can be counted across games. Controlled vocabulary
  (fixed so recurrence is countable — extending it is allowed but deliberate,
  and renaming a tag means updating old sidecars):

  `hanging-piece`, `unsafe-capture`, `wrong-recapture`, `missed-tactic`,
  `missed-mate`, `slow-mate`, `king-safety`, `unsafe-king-move`,
  `pawn-break-timing`, `conversion-drift`, `promotion-race`,
  `endgame-technique`, `opening-principle`, `time-trouble` (reserved until
  clock data exists).

- `drillLinks` — 1–3 `{ label, url }` practice links picked from
  `tools/drill-links.json` by the mistake's tags ("where to practice", rendered
  at the bottom of the takeaways box). Only use URLs from that file:
  lichess.org cannot be fetched from this sandbox, and every URL in the file
  traces back to the verified list in
  `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.md`.

With Maia data, let typicality steer the diagnosis: a mistake many peers share
(`recurrenceRisk` high) is a **knowledge gap** — write a pattern to drill; a move
almost nobody at the user's level plays is an **attention lapse** — write a
blunder-check habit, not a chess lesson. When `humanBest` is present, make it the
move the explanation teaches (the engine's pick gets a mention, not the lesson),
and quote the percentages where they sharpen the point ("88% of your peers
recapture with the rook").

Also write a 2–4 sentence `summary` of the whole game and an eye-catching serif
`title`/`subtitle` for the page header (the `<em>…</em>` and `<br>` tags carry the
house style — see `games/` for examples).

### 4. Generate the page

- Output file: `games/YYYY-MM-DD-HH-MM-<white>-vs-<black>.html`
  - `YYYY-MM-DD`: the game date from the PGN if complete, otherwise today.
  - `HH-MM`: the current time, 24h format (distinguishes several games analyzed the same day).
  - Names kebab-cased, lowercase.
- Copy `template.html` and replace **only** the `const GAME = { … };` statement inside
  the marked `GAME DATA` block, plus the static `<title>`. Never edit the template's
  markup, CSS, or scripts in a generated file — if something needs fixing, fix
  `template.html` itself so all future pages benefit.

Regex that does the replacement safely (Python, `re.S`):
`re.subn(r"const GAME = \{.*?\n\};", new_game_js, html, count=1, flags=re.S)`

- **Save the source game data.** Store the game exactly as the user gave it —
  headers/metadata **and** the full PGN movetext — verbatim in `pgn/`, as a `.txt`
  file whose name matches the generated page. For `games/<stamp>-<white>-vs-<black>.html`
  the source lives at `pgn/<stamp>-<white>-vs-<black>.txt`. This keeps the raw input
  next to the page it produced, so any game can be re-analyzed later. Write the PGN
  before (or alongside) the page, and commit it together with the page and the
  analysis sidecar (step 4b) — the three files ship as one unit.

### 4b. Write the analysis sidecar

The pipeline already computed everything; persist it so later sessions can
count recurrence, draw trends, and build drills **without re-running engines**.
For each game write `analysis/<stamp>.json` (same filename stamp as the page)
and commit it together with the page and the PGN. Schema (`schema: 1`):

```jsonc
{
  "schema": 1,
  "game": { "white": "…", "black": "…", "result": "…", "date": "…",
            "event": "…", "opening": "…", "userColor": "white",
            "pgnFile": "pgn/<stamp>.txt", "pageFile": "games/<stamp>.html" },
  "engine": { "stockfish": "depth 20", "maia": "…", "generated": "…" },
  "plies": [ {              // one entry per HALF-MOVE of the game
    "ply": 0, "san": "d4", "uci": "d2d4", "user": true,
    "phase": "opening",                       // "opening" | "middlegame" | "endgame"
    "fenBefore": "…",                         // full FEN before the move
    "evalBefore": 0.2, "evalAfter": 0.3,      // numeric pawns, user's perspective;
                                              //   mates as {"mate": 3} (negative =
                                              //   user gets mated; a game-over mate is
                                              //   {"mate": 0, "winner": "user"|"opponent"})
    "winBefore": 52.1, "winAfter": 48.7,      // win% (step 2c), user's perspective
    "bestUci": "g1f3",                        // engine's best from fenBefore
    "evalBest": 0.3,                          // user moves: eval after the best move
    "swing": -0.1,                            // user moves: evalAfter − evalBefore, on the
                                              //   ±10-pawn clamped scale
    "humanBestUci": "g1f3",                   // user moves on Maia pages
    "maia": { "1100": { "played": 0.31, "best": 0.22, "value": 0.55 }, "…": {} }
                                              // user moves: per band, probability of the
                                              //   played/best move and expected score of
                                              //   the position (side to move)
  } ],
  "accuracy": { "game": 87.2, "acpl": 34,
    "quality": { "inaccuracies": 3, "mistakes": 2, "blunders": 1 },
    "method": "…",                            // which game-accuracy aggregation was used
    "phases": { "opening": { "accuracy": 94.0, "acpl": 12,
                             "quality": { "…": 0 }, "plies": 20, "userMoves": 10 },
                "middlegame": {}, "endgame": {} } },
  "eloFit": { "best": 1100, "flat": true, "floor": true, "spread": 0.12,
              "positions": 43,                  // flat/floor/spread per the step-2b
                                                //   honest display rule; positions =
                                                //   count after the fit exclusions
              "logProbByBand": { "1100": -1.9, "…": 0 } },   // null on Stockfish-only runs
  "mistakes": [ {           // one per GAME mistake, same order; every GAME mistake
                            //   field (title, explanation, takeaways, …), plus:
    "tags": ["conversion-drift"],             // from the step-3 taxonomy
    "fenBefore": "…",
    "playedUci": "…", "bestUci": "…", "humanBestUci": "…",
    "winBefore": 92.1, "winAfter": 45.3,
    "retry": {                                // step-2d grading, reused by the
      "fen": "…",                             //   drill deck without engines
      "solutions": ["b2b1q"],                 // engine best + humanBest, deduped
      "acceptable": ["c1b2"],                 // within 0.5 pawns of best (multipv-5),
                                              //   minus solutions and the played move
      "legal": ["…"]                          // full legal-move list, sorted
    }
  } ]
}
```

Omit what wasn't computed (e.g. `maia`, `humanBestUci`, `eloFit` on a
Stockfish-only run) — like the GAME fields, every consumer treats sidecar
fields as optional. The sidecar is data for machines: numbers stay numeric
(no `−` typography, no `"%"` strings).

**Workflow rule**: write the sidecar alongside the page and commit the three
files together — `pgn/<stamp>.txt` + `games/<stamp>.html` +
`analysis/<stamp>.json`.

### 4c. Regenerate the drill deck

After writing the page and the sidecar, re-run the deck generator and commit
the refreshed deck **with** the game's files:

```bash
/tmp/chess-venv/bin/python tools/build-drills.py
```

It reads every `analysis/*.json`, backfills `retry` into any sidecar mistake
that lacks it (one Stockfish multipv-5 probe each, written back so the probe
runs once ever), and rewrites `drills/index.html` from `drills-template.html`
by replacing only the marked `const DRILLS = […];` block — the same
replace-only-the-data-block discipline as `template.html`. The output is
deterministic: running it twice is byte-identical. Fix deck UI issues in
`drills-template.html`, never in `drills/index.html`.

The deck front end keeps its schedule in `localStorage` (key
`chess-drills-v1`): a Leitner scheme keyed by `<stamp>:<ply>` — stable
across regenerations — with boxes 1–4 (fail → box 1, due immediately;
first-attempt solve → next box, due in 1/3/7 days). Due drills are
interleaved round-robin across source games, each drill ends with a
"recall the lesson" stage (the takeaway stays hidden until the user has
tried to state it), and a tag filter scopes a session to one weakness.

### GAME data reference

```js
const GAME = {
  title: "…",                 // page h1; HTML allowed (<br>, <em>)
  subtitle: "…",              // HTML allowed
  white: "…", black: "…",
  playerColor: "black",       // "white" | "black" — the user's side; board orients to it
  result: "1-0", date: "…", event: "…", opening: "…",   // free text, shown in header/footer
  movesSan: ["e4", "e5", …],  // full game, one SAN string per half-move
  summary: "…",               // default feedback-panel text; HTML allowed
  analysisNote: "…",          // footer: engines, depth, eval perspective, Maia band
  estimatedElo: "≈1300",      // OPTIONAL Maia fields — omit all of them on a
  estimatedEloNote: "…",      //   Stockfish-only page and the template renders as v1
  phaseElo: { opening: "≈1450 · 10 moves", middlegame: "…", endgame: "…" }, // any key omittable
  weakestPhase: "endgame",    // which phase chip gets the "weakest" highlight
  accuracy: "87%",            // OPTIONAL accuracy fields (step 2c) — Stockfish-only,
  acpl: 34,                   //   so they belong on every new page (number, not string)
  moveQuality: { inaccuracies: 3, mistakes: 2, blunders: 1 },   // ?! / ? / ?? stat strip
  phaseAccuracy: { opening: "94%", middlegame: "88%", endgame: "71%" }, // merged into the
                              //   phase chips (or shown alone when no phaseElo)
  evals: [52.1, 48.7, /*…*/], // OPTIONAL (step 2c): win% after each half-move, user's
                              //   perspective, one number per movesSan entry — the whole
                              //   series or nothing. Renders the clickable eval graph
                              //   under the board (rust dots = mistakes, two-way synced
                              //   with the replay); omitted → no graph, exactly as v1–3.
  moveNotes: [{               // one entry per USER move — puts the arrows (played,
                              //   engine's pick, human-findable) and the legend with
                              //   the move names on EVERY move the user made, not
                              //   just the mistakes. The played arrow is derived
                              //   in-page from the replay. Plies that have a
                              //   `mistakes` entry may be omitted (mistakes win).
                              //   Identical arrows (played == best, etc.) render
                              //   side by side automatically.
    ply: 4,                   // 0-based, same convention as mistakes
    best: "Nf3",              // engine's pick (SAN) — Stockfish only, so this
    bestArrow: ["g1","f3"],   //   array belongs on Stockfish-only pages too
    humanBest: "Nc3",                   // REQUIRED on a Maia page, on every entry
    humanBestArrow: ["b1","c3"]         //   (often equals best/played — emit it
  }, …],                                //   anyway; identical arrows split apart)
  mistakes: [{                // most important first — this is the display order
                              //   (with Maia: swing × recurrence, mates first)
    ply: 17,                  // 0-BASED index into movesSan of the move PLAYED.
                              //   ply 0 = White's move 1, ply 1 = Black's move 1,
                              //   ply 17 = Black's move 9. Clicking the mistake shows
                              //   the position BEFORE this move, with the arrows.
    played: "b5", best: "Kd8",          // SAN
    evalBefore: "−2.11",                // user's perspective, string as displayed
    evalAfter: "−3.53",                 // after the played move
    evalBest: "−1.99",                  // after the engine's move
    swing: "−1.42",                     // badge text; use "mate" when mate was allowed
    title: "…",
    explanation: "…",                   // HTML allowed
    playedArrow: ["b7","b5"],           // rust arrow, from→to
    bestArrow: ["e8","d8"],             // gold arrow, from→to
    winBefore: "92%", winAfter: "45%",  // OPTIONAL win% framing (step 2c): the feedback
                                        //   panel shows "your winning chances: 92% → 45%"
    tags: ["conversion-drift"],         // OPTIONAL, 1–3 from the step-3 taxonomy → card chips
    drillLinks: [{ label: "Hanging pieces — Lichess puzzle theme",
                   url: "https://lichess.org/training/hangingPiece" }],
                                        // OPTIONAL, 1–3 from tools/drill-links.json →
                                        //   "where to practice" list in the takeaways box
    playedPopularity: "38%",            // OPTIONAL Maia fields, per mistake:
    bestFindability: "6%",              //   share of the user's level playing/finding these
    humanBest: "Nf5",                   // human-findable move — REQUIRED on a Maia
    humanBestArrow: ["d3","f5"],        //   page even when equal to `best` (cream
    humanBestFindability: "47%",        //   arrow always; find-row cites it only when it differs)
    expectedPointsLost: "−0.21",        // human-outcome cost in expected score; OMIT when
                                        //   it rounds to ±0.00 (winBefore/After carry it)
    recurrenceRisk: "high",             // "high" | "medium" | "low" → card tag
    retry: {                            // OPTIONAL retry-mode grading (step 2d);
      fen: "…",                         //   when present the card gets a "↻ retry"
      solutions: ["b2b1q"],             //   chip and the board takes click-to-move
      acceptable: ["c1b2"],             //   input: solutions → solved, acceptable →
      legal: ["…"]                      //   "also fine", other legal → one more try
    },                                  //   then reveal; illegal clicks ignored
    takeaways: [{ lesson: "…", detail: "…" }, …]   // plain text
  }, …]
};
```

When any mistake carries `retry`, the page also shows a **practice first**
toggle above the mistake list (persisted in `localStorage`): with it on,
clicking a mistake card starts a retry instead of revealing the coaching, so
every mistake is attempted before it is read — retrieval practice first,
explanation second.

Conventions: all evals from the **user's** perspective (positive = good for the user);
mate scores as `#3` / `#−2` (negative = user gets mated). Use the minus sign `−` in
displayed evals to match the house style.

### 5. Update the games index

`games/index.html` lists every analyzed game, **newest first**, one clickable
`<a class="game-card">` entry per page. After generating a new page, add its entry
between the `GAME LIST` / `END GAME LIST` comment markers, keeping the list sorted
by the filename's `YYYY-MM-DD-HH-MM` stamp in descending order (new entries usually
go at the top). Each entry carries:

- `href`: the page's filename (relative, same folder);
- `.gc-date` / `.gc-time`: the date and time from the filename (`2026-07-05` / `14:50`);
- `<h2>`: the page's `GAME.title` with `<br>` flattened to a space (keep the `<em>`);
- `.gc-players`: `White vs Black · <span class="result">RESULT</span> · played COLOR`.

Copy an existing entry and edit it — never change the index's markup or CSS outside
the list. Verify every `href` in the index resolves to a file in `games/`.

Above the game list sits a separate `TOOLS` / `END TOOLS` marked region
holding the standing links (currently the drill-deck card pointing at
`../drills/index.html`). Like the game list, edit only inside the markers;
game entries never go in the TOOLS region and tool links never go in the
game list.

### 6. Verify before delivering

Playwright and Chromium are pre-installed (`NODE_PATH=/opt/node22/lib/node_modules`,
browser auto-found via `PLAYWRIGHT_BROWSERS_PATH`). Load the generated file headless and check:

- `window.__review.error` is `null` and the `#error-banner` is hidden — a non-null
  error means a bad SAN or wrong movetext; **fix the data, never ship a page with the banner**.
- `window.__review.total()` equals the number of half-moves in the PGN.
- `window.__review.placement(total)` equals `board.board_fen()` from python-chess
  after replaying the PGN — this proves the in-page replay matches the real game.
- Clicking each `.mistake-card` puts `window.__review.getPly()` on the mistake's `ply`
  and gives `#fb-panel` the `mistake-active` class.

Also sanity-check every `mistake.ply` points at the right move:
`movesSan[ply]` must equal `mistake.played`.

For `moveNotes` (any page that carries them):

- every user move has an annotation: each user ply appears in `moveNotes` or in
  `mistakes` (`window.__review.noteAt(ply)` must be non-null for all of them);
- every note's `best` is **legal** in the position before its `ply`
  (python-chess `parse_san`) and `bestArrow` matches that move's UCI;
- in the Playwright pass: stepping onto any user-move position shows the legend
  (with the played and engine's-pick SANs) and draws the arrows; when the played
  move equals the engine's pick, the two arrows render side by side — thinner,
  offset, not stacked (two `.arrow` line elements with equal from→to but
  different positions); opponent-move positions show no arrows and no legend.

When the page carries Maia data, also check:

- **every** `moveNotes` entry and **every** mistake carries `humanBest` +
  `humanBestArrow` — a Maia page where any user move lacks them is broken data
  (the human-findable move always exists; at worst it equals the engine's best).
  In the Playwright pass this means the cream arrow and the "human-findable"
  legend item are visible on **every** user-move position, without exception;
- every `humanBest` is **legal** in the position before its `ply` (python-chess
  `parse_san`) and its re-checked Stockfish eval is within tolerance of best;
- percentage fields parse as percentages, `expectedPointsLost` as a signed number;
- in the Playwright pass: the header strength line is visible iff `estimatedElo`
  is set, each mistake card shows a `.recur-tag` iff it has `recurrenceRisk`, the
  feedback panel shows the `.typ-badge` and `.find-row` iff the fields are set,
  and the cream arrow + "human-findable" legend appear only on positions whose
  mistake or move note has `humanBestArrow`;
- sanity: the Maia probability of the user's actual moves should average well
  above random at the fit band — if it doesn't, the FENs and moves are misaligned;
- `estimatedElo` obeys the step-2b honest display rule: `"unclear"` iff the
  sidecar's `eloFit.flat` is true, else `"≤1100"` iff `eloFit.floor`, else
  `"≈<band>"` with the band equal to `eloFit.best` — a flat or floor fit must
  never render as a confident middle number.

For the version-3 fields (any page that carries them):

- the header stat strip (`#head-stats`) is visible iff `accuracy` / `acpl` /
  `moveQuality` is set; phase chips show the phase accuracy iff
  `phaseAccuracy` is set;
- each mistake card shows tag chips (`.tag-chip`) iff the mistake has `tags`,
  and every tag is in the step-3 vocabulary;
- the feedback panel shows the win% row (`.win-row`) iff `winBefore`/`winAfter`
  are set, and the drill-links list (`.drill-links`) iff `drillLinks` is set;
  every drill URL comes from `tools/drill-links.json`;
- math sanity: win% values follow the step-2c formula (cp 0 → 50%, symmetric
  around 50 for ±cp), accuracy ∈ [0, 100], and `expectedPointsLost` never
  displays as "±0.00" (omit it instead);
- the sidecar exists at `analysis/<stamp>.json`, every `plies[i].san` replays
  legally with python-chess, its mistakes match the page's GAME mistakes
  (ply / played / best), and their `tags` are all from the vocabulary.

For the eval graph (any page with `evals`):

- `evals` has exactly one entry per half-move, every value is within
  [0, 100], and each equals the step-2c win% after that ply (a ply where the
  user delivers mate plots near 100, one where the user gets mated near 0);
- in the Playwright pass: the graph (`#eval-graph`) is visible iff `evals`
  is set; the polyline has plies + 1 points; clicking a rust `.graph-dot`
  behaves exactly like clicking that mistake's card (`getPly()` lands on the
  mistake's ply, `#fb-panel` gains `mistake-active`, and with the
  practice-first toggle on it starts a retry); `graphClick(ply)` /
  clicking mid-graph jumps the replay; stepping the replay moves the cursor
  (`graphPly()` tracks `getPly()`). On a page without `evals`, no graph
  renders and `graphPly()` returns null.

For retry mode and the drill deck (version 4):

- **retry data**, for every mistake with `retry` (page and sidecar):
  `solutions ⊆ legal`, `acceptable ⊆ legal`, `solutions ∩ acceptable = ∅`,
  every UCI legal per python-chess in `retry.fen`, `retry.fen` equals the
  mistake's `fenBefore`, `solutions` contains the mistake's `best` in UCI,
  and the played move appears in neither list;
- **retry UI** (Playwright, via the `window.__review.retryStart(i)` /
  `retryPlay(uci)` / `retryState()` hooks): starting a retry hides the
  arrows, legend, and eval compare; playing a solution flips the state to
  `solved` and reveals the feedback with the `.retry-result` banner; a wrong
  legal move leaves one more try, a second one reveals; an illegal UCI or
  click changes nothing; navigating away cancels the retry. Old pages
  (no `retry` fields) still load with `__review.error === null` and show no
  `.retry-chip` and no practice-first toggle;
- **drill deck**: after re-running `tools/build-drills.py` twice, the output
  is byte-identical; the deck's entry count equals the total number of
  sidecar mistakes; every drill's source-game link resolves to a file in
  `games/`; in Playwright (`window.__drills` hooks): solving a drill
  advances its Leitner box and survives a reload, failing one sends it to
  box 1 and re-queues it, the tag filter leaves only matching drills, the
  lesson stays hidden until the recall button is clicked, and the headless
  console shows no script errors.

Then commit the new page together with its `pgn/*.txt` source, its
`analysis/*.json` sidecar, the regenerated `drills/index.html`, and the
updated `games/index.html`, and push.

## Repo layout

- `template.html` — the interactive review template (self-contained; SAN replayer,
  board renderer, feedback panel, mistake list). Ships with demo placeholder data.
- `games/` — one generated HTML page per analyzed game.
  `games/2026-07-06-11-54-morphy-vs-duke-of-brunswick-count-isouard.html` is a worked
  example; match its tone and depth of annotation.
- `pgn/` — the raw source for each analyzed game (metadata + PGN movetext), one `.txt`
  file per page with a matching filename (`pgn/<stamp>-<white>-vs-<black>.txt`
  pairs with `games/<stamp>-<white>-vs-<black>.html`). Saved in workflow step 4.
- `analysis/` — one machine-readable sidecar per analyzed game
  (`analysis/<stamp>.json`, workflow step 4b): per-ply FENs/evals/win%,
  per-band Maia numbers, accuracy/quality tallies, Elo fit, and the tagged
  mistakes. The foundation later parts of the learning-loop series read.
- `games/index.html` — the game list: one link per analyzed game, newest first.
  Must be updated whenever a page is added (see workflow step 5). Also hosts
  the `TOOLS` marked region with the drill-deck link.
- `drills-template.html` — the drill-deck template (self-contained; FEN board
  renderer, click-to-move grading, Leitner scheduler, lesson-recall stage).
  Only its `const DRILLS = […];` block is replaced in the generated deck.
- `drills/index.html` — the generated drill deck covering every sidecar
  mistake. Never edited by hand: regenerate with `tools/build-drills.py`
  (workflow step 4c).
- `tools/build-drills.py` — the deck generator; also backfills step-2d
  `retry` objects into sidecars that predate them.
- `tools/maia/` — the Maia harness for workflow step 2b: `setup.sh` (fetches and
  patches the zerofish WASM engine, downloads the Maia-1 weights), `serve.mjs`
  (COOP/COEP static server), `host.html` + `query.cjs` (batch UCI queries through
  headless Chromium). `vendor/` and `weights/` are gitignored, re-fetched per session.
- `tools/drill-links.json` — the mistake-taxonomy → Lichess practice-link map
  used for `drillLinks` (workflow step 3). Only verified URLs; do not add
  unverified ones (lichess.org is unreachable from this sandbox).
- `docs/` — the design plans behind the template and this workflow;
  `docs/0003-plan-maia-engine.md` is the plan version 2 implements,
  `docs/0005-plan-learning-loop-1-foundation.md` the version-3 foundation,
  `docs/0006-plan-learning-loop-2-practice.md` the version-4 practice layer.
