# Drill & Review UI Tweaks — played-move arrow, stable button positions

**Scope**: three small UI changes, two on the drill deck
(`drills-template.html` → `drills/index.html`) and one on the game review
page (`template.html` → `games/*.html`). No analysis parameters change and no
GAME or sidecar field is added. The only data change is one new field on each
DRILLS entry (`playedUci`), which `tools/build-drills.py` derives.

**Common goal**: when you tap through a drill or a game, the buttons you tap
should stay in the same place, and a revealed drill should show the same
visual language as the review pages: rust for the move you played, gold for
the engine's move, cream for the human-findable move.

## Context — repo essentials (self-contained)

- `drills-template.html` is the drill-deck template. `tools/build-drills.py`
  rebuilds `drills/index.html` by replacing only its `const DRILLS = […];`
  block. Running the builder twice must give byte-identical output. UI fixes
  go in the template and never in `drills/index.html`.
- `template.html` is the game-review template. Generated pages under
  `games/` replace only `const GAME = {…};` and `<title>`. UI fixes go in the
  template.
- The rust colour is `--rust: #c1502f` in both templates. Review-page arrows
  draw it at 80% alpha as `"#c1502fcc"` (`template.html`, the
  `renderPosition` arrow specs). Drill arrows already use the same
  `<hex>cc` convention: gold `#c9a24bcc`, cream `#e7d7abcc`.
- `tools/verify-game.py` / `tools/verify-game.cjs` treat the legend as hidden
  when `el.hidden` is true or `offsetParent === null`
  (`hiddenOrAbsent`). Any change to how the legend is hidden must keep the
  `hidden` attribute as the signal, so those checks keep working.

---

## 1. Drill deck: show the played move as a rust arrow on reveal

**Today**: `revealSolution()` (`drills-template.html`) draws only the gold
best-move arrow and the optional cream human-findable arrow. The move you
actually played in the game appears only as text in the panel ("In the game
you played Nf6.").

**Change**: every reveal draws a third arrow for the game move, in rust.
This covers a first-try solve, an "also fine" answer, two failed attempts,
and the "Show the answer" button. The arrow uses the review page's exact
colour string, `"#c1502fcc"`, and the legend gains a matching rust item,
"played <SAN>".

**"Top level", so every puzzle gets it:**

1. **Data (`tools/build-drills.py`)**: add `"playedUci"` to every drill
   entry in `build_drills()`. Prefer the sidecar mistake's `playedUci`. When
   an older sidecar lacks it, derive it from the SAN:
   `chess.Board(retry["fen"]).parse_san(mistake["played"]).uci()`. Every
   drill then carries the field, with no per-game exceptions. The output
   stays deterministic.
2. **Rendering (`drills-template.html`)**: in `revealSolution()`, push the
   rust spec **first** so it sits under the gold and cream arrows, matching
   the review page's played → best → human order:
   ```js
   const specs = [];
   if (drill.playedUci) specs.push({ from: drill.playedUci.slice(0, 2), to: drill.playedUci.slice(2, 4), color: "#c1502fcc" });
   specs.push({ from: bestUci.slice(0, 2), to: bestUci.slice(2, 4), color: "#c9a24bcc" });
   …
   ```
   `revealSolution` is the single path that `resolveDrill` (solve,
   acceptable, fail) and `giveUp` all go through, so one edit covers every
   outcome. `drawArrowSet` already places arrows with the same from→to side
   by side. The played move can never equal a solution, because retry data
   excludes it, but the grouping handles any shared squares anyway.
3. **Legend**: add
   `<span class="legend-item" id="legend-played"><i class="dot rust"></i><span id="legend-played-text">played</span></span>`
   as the first item of `#board-legend`. Also add `.dot.rust { background: var(--rust); }`
   if the drills stylesheet lacks it. Set its text in `revealSolution()`, and
   hide it (`hidden`) only if a drill somehow has no `playedUci`.
4. **Keep the text line**: keep "In the game you played …". Colour the SAN
   rust, the same way `.played-san` does on the review page, so the text
   and the arrow read as one thing.

**Regenerate**: `/tmp/chess-venv/bin/python tools/build-drills.py`, then run
it again and confirm the two outputs are byte-identical.

**Verify (headless, `window.__drills` hooks)**: for a sample of drills
covering each outcome (solve, acceptable, two wrong moves, reveal button),
check that after the reveal:
- the arrow layer has a rust `.arrow` element (stroke or fill `#c1502fcc`)
  whose from→to matches the drill's `playedUci`;
- `#legend-played` is visible and names `drill.played`;
- every entry in `DRILLS` has a legal `playedUci` in its `fen`, checked
  with python-chess.

## 2. Drill deck: "Show the answer" and "Next" at the top of the panel

**Today**: `renderPanelAwait()` and `renderPanelResolved()` both append the
`.drill-actions` row **last**. That row holds "Show the answer (counts as a
miss)" in the await state, and "Next drill"/"Finish" plus "Open the full
review ›" in the resolved state. The row therefore sits below variable-length
content (check note, instructions, tags, result banner, title, recall box),
and it moves every time the text changes.

**Change**: build the actions row immediately after the eyebrow(s), before
any other panel content, in both states:

```
drill 7 of 53 · from <game> · move 14      ← eyebrow (small titles)
[ Show the answer (counts as a miss) ]    ← await state
[ Next drill ]  Open the full review ›    ← resolved state, same slot
<ask / banner, notes, tags, recall …>
```

Details:
- **Same slot in both states.** "Next drill" must land exactly where "Show
  the answer" was, so tap, reveal and next form one motion. To get that,
  give the resolved panel the same eyebrow line as the await panel. Today
  the resolved eyebrow drops "drill X of N", so the line wraps differently
  and the button shifts. Compute the counter once when the drill starts,
  before `resolveDrill` changes `queue`/`doneCount`, and reuse it in both
  renders.
- The "Open the full review ›" link stays beside "Next drill" in the same
  row. It is small, and moving it keeps the whole actions row together.
- `#attempt-note` ("one more try") stays below the ask text. It must not sit
  between the eyebrow and the button, or the button would move on the
  first wrong move.
- Keep the element ids (`btn-give-up`, `btn-next`) so that the `__drills`
  hooks and keyboard handling are unaffected. Add a small bottom margin to
  `.drill-actions` so the row separates from the content below it.

**Verify**: in Playwright, the `getBoundingClientRect().top` of
`#btn-give-up` before the reveal must equal the top of `#btn-next` after it,
at desktop width and at 390 px mobile width. The recall stage, tag filter
and Leitner behaviour must still pass the existing drill-deck checks.

## 3. Review page: legend below the buttons, with its space always reserved

**Today** (`template.html`, `.board-col`): `#board-legend` sits **between**
the board and `.controls`, and `.legend[hidden] { display: none; }` removes
it. On opponent-move positions (and during a retry) the legend disappears,
so the ‹ › buttons jump up by the legend's height. Your next tap then misses
or hits a different button.

**Change**:
1. **Order**: move the `#board-legend` div to just **after** `.controls`,
   before `#move-counter`:
   ```
   board → controls (|« −10 ‹ › +10 »|) → legend → move counter → kbd hint → eval graph → time bar
   ```
   The buttons then sit directly under the board and never move.
2. **Reserved space**: the legend stops leaving the layout when it is
   hidden. Replace
   ```css
   .legend[hidden] { display: none; }
   ```
   with
   ```css
   .legend[hidden] { display: flex; visibility: hidden; }
   ```
   and give `.legend` a fixed `height` (one line: the 11 px mono text or
   the 9 px dot, whichever is taller, plus the existing gap) in place of
   today's `min-height: 14px`. Also add `flex-wrap: nowrap` explicitly, so a
   long "human-findable Nxe5+" on a narrow phone cannot wrap to a second
   line and change the height. If the three items don't fit at 390 px,
   shrink the gap or font inside a media query rather than allowing a wrap.
   The result is an invisible block of identical height that is always
   present, so nothing below it (move counter, eval graph, time bar, feedback
   panel on mobile) moves when you press the buttons.
3. The `hidden` attribute is still the on/off signal, so `renderPosition`
   (`$("board-legend").hidden = !note`) and retry mode need no changes.
   `hiddenOrAbsent` in `tools/verify-game.cjs` still reads `el.hidden`
   first, so the existing legend checks keep passing.
4. Inside the legend, `#legend-human` toggles on and off. Make sure it uses
   `visibility` too, or leave it in the row, so that toggling it changes
   neither the height nor the centring enough to matter. The height is
   what counts here; horizontal re-centring inside the fixed row is fine.

**Verify**: add to `tools/verify-game.cjs`, inside the existing
per-position stepping loop:
- `#btn-prev`'s `getBoundingClientRect().top` is identical on every ply
  (user moves, opponent moves, start position, retry mode);
- `#board-legend`'s top is greater than `.controls`' bottom (legend below
  the buttons);
- `#move-counter`'s top is identical on every ply (the reserved space
  works).

Then run `tools/verify-game.py` on every page and get `all checks passed`.

### Rolling the template change out to existing pages

The generated pages in `games/` (13 today) embed the old markup and CSS. A
template fix only reaches them if they are **re-templated**: for each
`games/*.html` other than `index.html`, take its `const GAME = {…};` block
and `<title>` verbatim, and splice them into a fresh copy of `template.html`
with the step-4 regex (`re.subn(r"const GAME = \{.*?\n\};", …, count=1, flags=re.S)`).
This is not a hand edit of a generated page. It re-runs the normal
generation with unchanged data, so the GAME block must come out
byte-identical, which the diff will show. No engine work and no sidecar
changes are needed. Run `tools/verify-game.py` on each page afterwards.

---

## Deliverables / commit checklist

- `tools/build-drills.py`: emits `playedUci` on every drill.
- `drills-template.html`: rust played arrow and legend item on reveal;
  actions row at the top of both panel states, with the same eyebrow in both.
- `drills/index.html`: regenerated, byte-identical when run twice.
- `template.html`: legend moved below `.controls`, reserved via
  `visibility: hidden` with a fixed one-line height.
- `games/*.html`: re-templated, with GAME blocks unchanged.
- `tools/verify-game.cjs`: button- and counter-position stability checks and
  the legend-below-controls check.
- `CLAUDE.md`: in the step-6 checklist, add the new stability assertion
  under the `moveNotes` Playwright bullet, and mention the rust played arrow
  in step 4c's deck description.
