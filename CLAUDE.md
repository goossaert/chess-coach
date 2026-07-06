# chess-coach

This repository turns chess games into interactive coaching pages. When the user
uploads a game and asks for feedback, analyze it and generate one HTML review page
per game in `games/`, built from `template.html`.

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

Select the **3–6 biggest mistakes by the user** (largest negative swings; a move that
allows mate always qualifies). Prefer instructive moments over near-duplicates.

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
  analysisNote: "…",          // footer: engine, depth, eval perspective
  mistakes: [{                // most important first — this is the display order
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

Then commit the new page together with the updated `games/index.html` and push.

## Repo layout

- `template.html` — the interactive review template (self-contained; SAN replayer,
  board renderer, feedback panel, mistake list). Ships with demo placeholder data.
- `games/` — one generated HTML page per analyzed game.
  `games/2026-07-06-11-54-morphy-vs-duke-of-brunswick-count-isouard.html` is a worked
  example; match its tone and depth of annotation.
- `games/index.html` — the game list: one link per analyzed game, newest first.
  Must be updated whenever a page is added (see workflow step 5).
- `docs/plan.md` — the design plan behind the template and this workflow.
