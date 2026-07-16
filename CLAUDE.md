# chess-coach

**Version 2**

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

1. **Estimated strength** — for every position where the user is to move (skip
   forced/only-move positions), get the probability each band assigns to the move
   actually played. The best-fit band maximizes the mean log-probability (floor
   tiny probabilities at 0.1% so one weird move can't dominate). Report it as
   `estimatedElo` ("≈1300"); if the fit is flat, say so in `estimatedEloNote`.
   Repeat per phase for `phaseElo` (opening ≈ first 10 full moves, endgame from
   when queens are off or few pieces remain, middlegame between; include the
   sample size, e.g. "≈1300 · 43 moves", and set `weakestPhase`). Small per-phase
   samples are normal — the ≈ carries the uncertainty.
2. **Per-mistake numbers**, at the best-fit band, for the 10–20 positions where
   Stockfish flagged a meaningful swing: `playedPopularity` = probability of the
   played move; `bestFindability` = probability of the engine's best move;
   `expectedPointsLost` = (expected score after the best move) − (expected score
   after the played move), both from the **user's** perspective — the after
   positions have the opponent to move, so use `1 − value`. Display as a signed
   number ("−0.21"), or "±0.00" when the human-outcome cost is negligible.
3. **The human-findable alternative** — when the engine's best move is
   near-unfindable at the user's level (roughly `bestFindability` < 10%), find the
   highest-probability move whose Stockfish eval (re-check at depth ~18) stays
   within 0.5 of best and is not losing. If it differs from the engine's best,
   emit `humanBest`, `humanBestArrow`, `humanBestFindability`. Never recommend an
   engine-only move as the lesson when a human-findable one keeps the eval.
4. **Per-move notes** — apply the same human-findable rule (item 3) to **every**
   user move, at the fit band, and finish the `moveNotes` entries started in
   step 2: each is `{ ply, best, bestArrow }` plus `humanBest`/`humanBestArrow`
   when a human-findable alternative exists for that ply. Skip plies covered by
   a `mistakes` entry — the template lets mistakes take precedence — and keep
   the eval re-checks cheap (depth ~18, only for plies where `bestFindability`
   < 10%).

**Mistake selection** — rank by **swing × recurrence likelihood** instead of raw
swing: weight each candidate's centipawn loss by `playedPopularity` (floored at
~5% so rare blunders still register). A −1.5 mistake that 35% of the user's level
repeats outranks a −3.0 one-off. A move that allows mate always qualifies, first.
Select 3–6 mistakes; prefer instructive moments over near-duplicates. Derive
`recurrenceRisk` from `playedPopularity`: ≥25% high, 10–25% medium, <10% low.

**Caveats**: most games in `pgn/` are against engines, whose off-beat play can
push positions outside Maia's human-vs-human training data — take probabilities
in weird positions with a grain of salt, and keep forced positions out of the Elo
fit. Percentages in the first ~5 moves are approximate too. Name the model and
conditioning band in `analysisNote` (e.g. "human model: Maia rating-band networks
(lc0 via zerofish WASM), conditioned at ≈1300; Maia-3 unreachable from this
sandbox, Maia-1 bands stand in").

**Fallback**: if the Maia setup fails (network policy can change), do the
Stockfish-only analysis and omit every Maia field — the template then renders
exactly as version 1. Say so in `analysisNote` and to the user.

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
  before (or alongside) the page, and commit the two together.

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
    humanBest: "Nc3",                   // OPTIONAL, same rule as in mistakes: only
    humanBestArrow: ["b1","c3"]         //   when best is near-unfindable at the
  }, …],                                //   user's level and this keeps the eval
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
    playedPopularity: "38%",            // OPTIONAL Maia fields, per mistake:
    bestFindability: "6%",              //   share of the user's level playing/finding these
    humanBest: "Nf5",                   // best human-findable move; only when it
    humanBestArrow: ["d3","f5"],        //   differs from `best` (drawn as a cream arrow)
    humanBestFindability: "47%",
    expectedPointsLost: "−0.21",        // human-outcome cost in expected score; "±0.00" ok
    recurrenceRisk: "high",             // "high" | "medium" | "low" → card tag
    takeaways: [{ lesson: "…", detail: "…" }, …]   // plain text
  }, …]
};
```

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

- every `humanBest` is **legal** in the position before its `ply` (python-chess
  `parse_san`) and its re-checked Stockfish eval is within tolerance of best;
- percentage fields parse as percentages, `expectedPointsLost` as a signed number;
- in the Playwright pass: the header strength line is visible iff `estimatedElo`
  is set, each mistake card shows a `.recur-tag` iff it has `recurrenceRisk`, the
  feedback panel shows the `.typ-badge` and `.find-row` iff the fields are set,
  and the cream arrow + "human-findable" legend appear only on positions whose
  mistake or move note has `humanBestArrow`;
- sanity: the Maia probability of the user's actual moves should average well
  above random at the fit band — if it doesn't, the FENs and moves are misaligned.

Then commit the new page together with its `pgn/*.txt` source and the updated
`games/index.html`, and push.

## Repo layout

- `template.html` — the interactive review template (self-contained; SAN replayer,
  board renderer, feedback panel, mistake list). Ships with demo placeholder data.
- `games/` — one generated HTML page per analyzed game.
  `games/2026-07-06-11-54-morphy-vs-duke-of-brunswick-count-isouard.html` is a worked
  example; match its tone and depth of annotation.
- `pgn/` — the raw source for each analyzed game (metadata + PGN movetext), one `.txt`
  file per page with a matching filename (`pgn/<stamp>-<white>-vs-<black>.txt`
  pairs with `games/<stamp>-<white>-vs-<black>.html`). Saved in workflow step 4.
- `games/index.html` — the game list: one link per analyzed game, newest first.
  Must be updated whenever a page is added (see workflow step 5).
- `tools/maia/` — the Maia harness for workflow step 2b: `setup.sh` (fetches and
  patches the zerofish WASM engine, downloads the Maia-1 weights), `serve.mjs`
  (COOP/COEP static server), `host.html` + `query.cjs` (batch UCI queries through
  headless Chromium). `vendor/` and `weights/` are gitignored, re-fetched per session.
- `docs/` — the design plans behind the template and this workflow;
  `docs/0003-plan-maia-engine.md` is the plan version 2 implements.
