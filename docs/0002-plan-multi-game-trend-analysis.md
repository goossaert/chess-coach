# Multi-Game Trend Analysis & Study Checklist — Plan

## Context

Until now the repo has produced **one coaching page per game** (see `docs/0001-plan-interactive-chess-review-template.md`). The user asked for the first **cross-game** deliverable: aggregate every game they have played, find what keeps going wrong, and turn that into a prioritized training plan backed by Lichess material. A follow-up request (run separately) added an interactive HTML version of the resulting report with persistent checkboxes, so the study plan can be worked through over time.

### Request 1 — the trend-analysis report

The user's request, restated:

- Look at the **`pgn/` folder** and analyze **all games played by the user** (they play under the name **"Anonymous"** — the color they held in each game is read from the PGN `White`/`Black` headers).
- Identify the **most common mistakes** they made, using **Stockfish** for the analysis.
- Find **studies/exercises on Lichess.org** that would help close those gaps.
- Organize the output with **one section per mistake category**; under each section list the studies/exercises that cover it, **sorted with the most relevant and impactful first**. Up to **100 URLs per section** are allowed if useful and relevant (a cap, not a target).
- The report **may include other advice and takeaways** judged useful or important, formatted however is most effective (whole sections, sub-sections, etc.).
- Output is written as a **report in the `report/` folder** (the folder was later renamed to `reports/`); at the **bottom of the report**, list the **source PGN files** and the **corresponding game pages** (`games/` folder) used for the analysis.

### Request 2 — the HTML checklist version (follow-up, voice-transcribed)

The user's request, restated (transcription said "Liches"/"leads" — meaning Lichess/links):

- Take the markdown report in the `report/` folder and create an **HTML file with the exact same content and formatting**, written **inside the `report/` folder as well**.
- Under each section of the report there is a **list of links to the Lichess website**: turn those lists into checklists with a **checkbox in front of every item**.
- When the user ticks a checkbox, its state is **saved in the browser's local storage**, so reopening the page later shows which items were already checked.
- This must **work on Safari on iOS**.
- **Do not change anything in the markdown file** — the HTML file mirrors its content and formatting exactly.

## Deliverables

| File | Purpose |
|---|---|
| `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.md` | The cross-game trend-analysis report (Request 1) |
| `reports/2026-07-13-recurring-mistakes-and-lichess-study-plan.html` | Same content as the markdown, with persistent-checkbox link lists (Request 2) |
| `docs/0002-plan-multi-game-trend-analysis.md` | This plan |

## 1. Analysis method (Request 1)

- **Engine pass**: Stockfish (16, via `apt-get install stockfish`) driven by `python-chess` from a venv, per the setup in `CLAUDE.md`. For **every position where the user is to move** (all 7 games, ~310 moves): eval before the move, engine best move and its eval, eval after the played move — depth 20, evals always from the user's perspective.
- **Error mining**: flag moves losing ≥ 1.00 vs. the engine's best (centipawn losses clamped at ±10.00 so dead-won/dead-lost noise doesn't dominate), plus special detection for **missed forced mates**, **slower-than-necessary mates**, and **moves that walked into forced mate**.
- **Categorization**: classify every flagged move by the *mechanism* of the error (not the phase), merging near-duplicates across games into recurring categories. Order the categories by **aggregate cost across all games**.
- **Report structure**: a one-paragraph diagnosis + per-game scoreboard up top; then one section per category, each with an engine-evidence table (game, move, what happened, cost), the habit that fixes it, and the sorted Lichess resource list; then cross-cutting advice (pre-move ritual, time controls, sparring partners, weekly drill plan); methodology; and the sources appendix mapping each `pgn/*.txt` to its `games/*.html` page.
- **Link sourcing constraint**: lichess.org blocks direct fetches from the analysis environment, so every URL is verified via search-engine-indexed lichess.org results rather than by loading the page. Prefer durable URL families (`/practice/...`, `/training/<theme>`, `/study/<id>`) and note the caveat in the report.

As built, the analysis found six categories (hanging pieces & counting; unsafe captures & automatic recaptures; king safety; missed forcing wins; converting winning positions; opening habits) with 134 verified Lichess URLs.

## 2. HTML checklist version (Request 2)

- **Fidelity**: render the markdown to HTML with identical content and formatting — same headings, tables, emphasis, link text, and order. No rewording, no dropped or added items. The markdown file itself is untouched.
- **Checkboxes**: every list item in the per-section Lichess resource lists gets a leading checkbox. (Lists elsewhere in the report that are not Lichess link lists keep their normal formatting.)
- **Persistence**:
  - `localStorage`, one entry per item, keyed by a **stable identifier derived from the item's URL** (not its list position), so future edits to the report don't shift ticks onto the wrong items.
  - State is written on every change and re-applied on page load.
  - **iOS Safari specifics**: wrap all storage access in `try/catch` (Safari private browsing can throw on `setItem`); use standard `change` events on real `<input type="checkbox">` elements (correct tap behavior in Mobile Safari); no external JS dependencies. Note: localStorage is per-browser and Safari may evict storage for sites unused for extended periods (ITP) — acceptable for this use.
- **Self-contained**: single HTML file, inline CSS/JS, consistent with the repo's existing self-contained pages.

## Verification

- Report: every eval/claim in the evidence tables cross-checked against the engine JSON; every relative link in the sources appendix resolves; URL lists stay within the 100-per-section cap.
- HTML version: load headless (pre-installed Chromium + Playwright), assert content parity with the markdown (headings, item counts, link hrefs), tick checkboxes, reload, and assert the ticks survive; confirm no console errors.
- Work is committed on **`main` directly** (per the user's instruction for this documentation pass; the original report work was done on a feature branch and merged).
