# Chess Game Analysis Template — Plan

## Context

The user has an existing single-file HTML game review ("The Five Swings") that shows 5 static board positions — one per big mistake — each with an explanation and a before/played/best eval comparison. They want to turn this into a reusable system:

- A **`template.html`** with the same visual design, but with an **interactive, replayable board** (move-by-move, ±10 moves fast-forward/rewind) instead of static per-mistake boards.
- At mistake moments, **feedback appears next to the board**, including concrete **takeaways** ("what to retain / work on") formatted so they can be practiced and remembered.
- A **clickable list of the most important mistakes** that jumps the board to that moment and shows the feedback.
- A **`CLAUDE.md`** (user wrote "cloud.md") so that in future sessions, when the user uploads a game as a **PGN** file (user wrote "PNG", clearly meaning PGN) and asks for feedback, Claude Code knows to analyze it and generate one HTML file per game in a **`games/`** subfolder from the template.
- This plan saved as **`docs/plan.md`**.

The repo (`goossaert/chess-coach`) is currently empty except for a README. Work goes on branch `claude/chess-game-analysis-template-pno6qb`, committed and pushed.

## Deliverables

| File | Purpose |
|---|---|
| `template.html` | Self-contained interactive game-review template with placeholder data block |
| `CLAUDE.md` | Instructions for future Claude Code sessions (PGN → analysis → generated page) |
| `games/` | Output folder for generated per-game pages (seeded with one worked example) |
| `docs/plan.md` | This plan |

## 1. `template.html` design

Single self-contained file, no external JS libraries (fonts via Google Fonts as in the original). Reuses the original's visual language: `--bg #12161d`, panel `#181e27`, cream `#ece7da`, gold `#c9a24b`, rust `#c1502f`; Fraunces for headings, Inter for body, IBM Plex Mono for labels/evals; the card, swing-badge, legend, and 3-column compare styles; and the original's inline SVG chessboard style (45px squares, `#748a66`/`#eae6d9` squares, coordinate labels, cburnett piece `<defs>` copied from the uploaded file, rust/gold move arrows).

### Data block (what generation replaces)

One clearly delimited `<script>` block:

```js
// === GAME DATA — replace everything between these markers ===
const GAME = {
  title: "…", subtitle: "…",
  white: "…", black: "…", playerColor: "black",
  result: "0-1", date: "…", event: "…", opening: "…",
  movesSan: ["e4","e5","Nf3", …],           // full game in SAN, from the PGN
  summary: "2–3 sentence overall game narrative…",
  mistakes: [{
    ply: 17,                 // 0-based half-move index of the played mistake
    played: "Nd7", best: "axb4",
    evalBefore: "+2.03", evalAfter: "−1.54", evalBest: "+2.10",
    swing: "−3.57",
    title: "Retreated the wrong knight",
    explanation: "…paragraph like the original…",
    playedArrow: ["f6","d7"], bestArrow: ["a5","b4"],   // from→to squares
    takeaways: [
      { lesson: "Short imperative heuristic", detail: "How to apply/practice it" },
      …
    ]
  }, …]
};
// === END GAME DATA ===
```

Everything else in the page (header text, mistake cards, feedback panel, move list) is **rendered by JS from `GAME`**, so generation = copy template + replace one block. No HTML surgery needed.

### Move engine (in-template JS)

A small SAN interpreter (~250 lines) that starts from the initial position and applies `movesSan` one ply at a time, handling captures, castling (`O-O`/`O-O-O`), en passant, promotion (`e8=Q`), disambiguation (`Nbd2`, `R1e2`), and check/mate suffixes. It precomputes the board state for every ply at page load, plus last-move from/to squares for highlighting. If a move fails to parse, it renders a visible error banner naming the bad ply — so a generation mistake is caught immediately instead of silently showing a wrong position.

### Layout & interaction

- **Header**: same style as original — eyebrow (players/result/date), serif title, subtitle.
- **Board area**: SVG board (player's color at bottom) + last-move square highlight; at a mistake position, rust arrow (played) + gold arrow (engine's pick) + the played/pick legend.
- **Controls** under the board: `|« start`, `−10`, `‹ prev`, `next ›`, `+10`, `end »|`, with a mono move counter ("move 17 of 42 · Black played Ne5"). Keyboard: ←/→ single move, Shift+←/→ ±10, Home/End.
- **Feedback panel** beside the board (stacks below on mobile):
  - Default state: game summary.
  - When the current position is a mistake moment (the position **before** the played mistake, where the arrows make sense — also kept active on the ply just after): shows the mistake card content — move header + swing badge, explanation, the 3-column before/played/best compare, and a **"What to retain"** box listing each takeaway as a bold one-line lesson with a short how-to-practice line, styled so it reads like a drill card.
- **Mistakes list** below (cards restyled from the original, minus the static boards): move number, played vs best, swing badge, one-line title. **Clicking a card jumps the board to that ply**, activates the feedback panel, and marks the card active. Cards also get a marker in the move list.
- **Move list**: compact clickable SAN grid (two plies per row) with mistake plies flagged in rust; clicking any move jumps there; auto-scrolls with navigation.
- Footer in the original's mono style noting how the analysis was produced.

The template ships with tiny placeholder data (a short real game) so opening `template.html` directly shows a working page.

## 2. `CLAUDE.md` workflow instructions

Written for future sessions in this repo. Key content:

1. **Trigger**: user uploads/pastes a PGN (they may say "PNG" — treat as PGN) and asks for game feedback/analysis.
2. **Parse the PGN**: extract headers (players, result, date, event, opening) and the SAN move list; determine which color the user played (ask if not stated and not inferable, e.g. from a `White`/`Black` name they've used before).
3. **Analyze**: prefer a real engine — use `python-chess` + Stockfish if installed or installable in the session (`pip install chess`, `apt-get install stockfish`), analyzing each position to find the largest eval swings. If no engine is available, analyze by judgment and **label evals as estimates** in the page footer. Select the 3–6 biggest mistakes by the user's side.
4. **Write the coaching content** per mistake: explanation paragraph (concrete, names squares and plans, like the original), arrows (from/to squares for played and best move), and 1–3 takeaways each formatted as *lesson* (short imperative heuristic) + *detail* (how to apply it in future games). Plus a game `summary`.
5. **Generate the page**: copy `template.html` → `games/YYYY-MM-DD-HH-MM-<white>-vs-<black>.html` (kebab-case; `HH-MM` is the generation time in 24h format so multiple games analyzed the same day get distinct names), replace only the marked GAME DATA block, update `<title>`.
6. **Verify before delivering**: load the generated file headless (Playwright + the pre-installed Chromium at `/opt/pw-browsers/chromium`), check the page shows no move-parse error banner and the move count matches; if python-chess is available, cross-check the final position FEN. Then commit and push.
7. Conventions: 0-based `ply` indexing rule with a worked example; never edit template markup in generated files (fix the template instead); keep one HTML file per game.

## 3. Worked example in `games/`

Generate one real example page (a short annotated classic game, e.g. the Opera Game, with genuine mistake annotations) so the user immediately sees the end product and future sessions have a reference for tone/format of the coaching content.

## Verification

- Write a throwaway Node/Playwright script in the scratchpad that loads `template.html` and the example page in the pre-installed Chromium and asserts: no console errors, no parse-error banner, final board position matches the expected FEN (computed independently with python-chess), ±10/start/end buttons land on the right ply, clicking a mistake card jumps the board and shows the feedback panel with takeaways.
- Screenshot the example page (desktop + narrow width) to visually confirm the design matches the original's look.
- Commit and push everything to `claude/chess-game-analysis-template-pno6qb` (no PR unless asked).
