[← Back to index](../games/index.html)

# Recurring Mistakes & Lichess Study Plan

<!-- TREND:META -->
**Player:** Anonymous · **Games analyzed:** 9 (July 5 – July 15, 2026) · **Engine:** Stockfish, depth 20, every move you played · **Evals:** always from your perspective (positive = good for you)
<!-- END TREND:META -->

---

## The one-paragraph summary

You reached a **winning position (+3.3 or better) in six of the seven games and converted only two of them**. The games are not being lost in the opening or to deep strategy — they are lost in single moves: a piece put on a square the opponent covers, a "free" capture that turns out to be bait, a recapture made on autopilot, a pawn push that opens your own king. The engine data says the same thing seven different ways: **the leak is move-by-move safety checking, not chess knowledge.** The good news: this is the most trainable weakness in chess. Every section below has a drill plan.

### Scoreboard

<!-- TREND:SCOREBOARD -->
| Game | You played | Result for you | ACPL¹ | Accuracy | Mistakes² | Blunders³ | Peak eval |
|---|---|---|---|---|---|---|---|
| [2026-07-05 14:50 vs Stockfish](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | Black | **Won** | 63 | 73% | 2 | 2 | mate on the board |
| [2026-07-06 19:53 vs Stockfish](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) | White | Lost | 83 | 40% | 0 | 2 | mate on the board |
| [2026-07-09 12:11 vs Stockfish](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | White | Lost | 148 | 67% | 1 | 1 | +1.4 |
| [2026-07-09 17:46 vs Stockfish](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | White | **Won** | 30 | 92% | 0 | 0 | mate on the board |
| [2026-07-09 20:18 vs Stockfish](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | Black | Lost | 47 | 83% | 2 | 0 | +3.5 |
| [2026-07-11 15:49 vs Stockfish-level-3](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | Black | Lost | 143 | 60% | 4 | 1 | +5.3 |
| [2026-07-13 18:31 vs Stockfish-level-3](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | White | Lost | 124 | 60% | 1 | 2 | +8.1 |
| [2026-07-14 17:37 vs Maia 600](../games/2026-07-14-17-37-maia-600-vs-guest.html) | Black | **Won** | 30 | 94% | 0 | 0 | mate on the board |
| [2026-07-15 21:31 vs Maia 800](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | White | Lost | 38 | 87% | 0 | 1 | +5.7 |

¹ average centipawn loss vs. Stockfish's best move (each loss clamped to [0, 1000] cp). ² moves dropping your win probability by ≥20 points (?). ³ moves dropping it by ≥30 points (??).
<!-- END TREND:SCOREBOARD -->

### Where the points went

<!-- TREND:CATEGORIES -->
| Category | Mistakes | Games | Win% lost (total)⁴ | Worst single moment |
|---|---|---|---|---|
| `hanging-piece` | 8 | 6 | −284 | [66.Be5?? (07-06 19:53 (W))](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) |
| `missed-tactic` | 8 | 7 | −207 | [29.Qg4?? (07-09 12:11 (W))](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) |
| `wrong-recapture` | 3 | 3 | −67 | [24…Rxh5?? (07-11 15:49 (B))](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) |
| `opening-principle` | 4 | 3 | −66 | [6…Nb4? (07-05 14:50 (B))](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) |
| `conversion-drift` | 3 | 3 | −54 | [25.Rd6?? (07-15 21:31 (W))](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) |
| `pawn-break-timing` | 3 | 3 | −45 | [21…g5? (07-09 20:18 (B))](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) |
| `endgame-technique` | 2 | 2 | −40 | [63.g3?? (07-06 19:53 (W))](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) |
| `unsafe-capture` | 4 | 4 | −26 | [35.Qxb2?! (07-13 18:31 (W))](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) |
| `unsafe-king-move` | 2 | 1 | −22 | [33.Kd6?! (07-15 21:31 (W))](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) |
| `king-safety` | 1 | 1 | ≈0 (missed wins, not losses) | [41…c4 (07-09 20:18 (B))](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) |
| `missed-mate` | 3 | 3 | ≈0 (missed wins, not losses) | [36…Ra2 (07-05 14:50 (B))](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) |

⁴ each analyzed mistake counted once, under its first taxonomy tag; cost = win-probability points lost on that move (winBefore − winAfter from the sidecar).
<!-- END TREND:CATEGORIES -->

The curated study sections below keep their original order; the table above carries the current cost ranking. Within each category, studies/exercises are sorted with the most relevant and impactful first. (Free lichess account recommended — it tracks your puzzle history and unlocks the dashboard.)

---

## 1. Pieces left en prise — you don't count attackers and defenders on the landing square

**This appeared in all seven games and is the single biggest leak.** The pattern: you decide where a piece *wants* to go and play it there without asking the mechanical question, *"how many enemy pieces touch that square, and how many of mine defend it?"* — or you move a piece without asking what it was defending.

What the engine found:

<!-- TREND:EVIDENCE tags=hanging-piece -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-06 19:53 (W)](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) | 66.Be5?? | Stepped next to the enemy bishop instead of taking it | 93% → 9% | −42.21 |
| [07-13 18:31 (W)](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | 33.Bh5?? | The bishop landed on the knight's square | 79% → 22% | −7.27 |
| [07-05 14:50 (B)](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | 17…Ne5?? | Parked a knight on e5 that nobody actually guarded | 78% → 30% | −5.95 |
| [07-13 18:31 (W)](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | 8.Ne4? | Two pieces on one pawn's path | 66% → 38% | −3.24 |
| [07-05 14:50 (B)](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | 23…Ng4? | Reassigned the bodyguard and left h5 to the rook | 88% → 64% | −4.51 |
| [07-09 12:11 (W)](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | 17.b4?! | b4 instead of b3 — and the a4-knight simply fell | 31% → 13% | −2.99 |
| [07-11 15:49 (B)](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | 25…Bh3?! | The toughest defence was still on the board | 24% → 10% | −3.16 |
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 30…Rg5?! | Traded rooks on a square the sleeping bishop could see | 16% → 5% | −3.23 |
<!-- END TREND:EVIDENCE -->

**The habit to build:** before *releasing* any piece (or pawn), name out loud every enemy unit that attacks the landing square — including bishops still sitting on their home squares behind pawns (that's exactly how 33.Bh5 and 17…Ne5 died) — and everything the moving piece was defending. This is a 5-second scan; it would have saved roughly four of these seven games.

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/training/hangingPiece — the Hanging Piece puzzle trainer. Do 10/day for a month. This is *your* theme: it drills spotting pieces that can simply be taken.
2. https://lichess.org/study/qAT8DEcG — *Counting attackers/defenders* — the exact skill of tallying a square before landing on it.
3. https://lichess.org/study/lib2mgJf/Y48PAStF — *Counting Attackers & Defenders 3* — more counting reps, including when the count lies (piece values in the capture sequence).
4. https://lichess.org/study/899jbI8q — *Board Vision* — trains seeing the whole board, including long-range pieces behind blockers.
5. https://lichess.org/study/i52i2RZd/qKXcBHbx — *Winning Tactics — Loose Pieces Drop Off (LPDO)* — the classic "loose piece" mantra, from the punishing side; teaches you to keep a mental list of undefended pieces (yours and theirs).
6. https://lichess.org/study/6fNfJhyQ — *Undefended Pieces* — spotting exercises.
7. https://lichess.org/study/3eLEBsD5 — *Hanging Pieces* (NM kstorn) — themed exercise set.
8. https://lichess.org/study/UO1jtDDb — *Hanging Pieces lesson* — guided lesson format.
9. https://lichess.org/study/9iiz4N01/e1POUvNw — *Beginner Strategy Class — Hanging Pieces* — slower, explained examples.
10. https://lichess.org/study/FCFA1NuF/yLtHgiLd — *Hanging piece study* — extra reps.
11. https://lichess.org/study/ZukDFo3z/xPavTrls — *Capture & Defend Beginner* — attack/defense counting from both sides.
12. https://lichess.org/study/rZHYOYSU — *Piece Capture, Counting and more!* — counting drills with piece-value twists.
13. https://lichess.org/study/w7TzU82u — *Attack and capture for beginners* — foundation reps if the above feel fast.
14. https://lichess.org/training/fork — Fork trainer: your unguarded pieces are what forks hit; punishing forks trains spotting them.
15. https://lichess.org/study/9fFjmVYl/f6JRV0kH — *Double Attack Puzzles* — same skill from the winning side.
16. https://lichess.org/study/yJEO1s42/QOxTr8YH — *Double Attacks* — more of the same.
17. https://lichess.org/study/bXJ7Y4eU — *Double Attack + Pin puzzles* — mixed set.
18. https://lichess.org/video/Ao9iOeK_jvU — video: *Chess Fundamentals #1: Undefended Pieces*.
19. https://lichess.org/video/Iu1f7axtccQ — video: *How to identify Hanging Pieces* (IM Alex Astaneh) — includes the counting method.
20. https://lichess.org/forum/general-chess-discussion/quick-and-accurate-method-of-counting-multiple-captures — forum thread: fast counting technique on contested squares.
21. https://lichess.org/forum/general-chess-discussion/loose-pieces-drop-off-how-to-stop-blundering?page=3 — forum thread: practical anti-blunder routines from other improvers.

---

## 2. Unsafe captures and automatic recaptures — "why am I allowed to take this?"

**Three of the four lost-from-winning games flipped on a single capture.** Two flavors: (a) the *automatic recapture*, played instantly because "he took, so I take back", which opens a line or walks into a tactic; (b) the *poisoned gift* — a piece offered as bait for a fork or mating net, and you took it.

What the engine found:

<!-- TREND:EVIDENCE tags=unsafe-capture,wrong-recapture -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-11 15:49 (B)](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | 24…Rxh5?? | The recapture that gave the game back | 60% → 20% | −5.06 |
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 22…fxg5? | The automatic recapture opened the diagonal that forked you | 56% → 32% | −2.44 |
| [07-13 18:31 (W)](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | 35.Qxb2?! | Took the bishop, dropped the diagonal, walked into mate | 13% → 2% | mate |
| [07-09 12:11 (W)](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | 26.Bxh5 | Grabbed a pawn on h5 while your king burned on c1 | 10% → 2% | −9.31 |
| [07-09 17:46 (W)](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | 20.Rxc6 | Grabbed the c6-pawn and lost a knight in the wash | 94% → 90% | −1.80 |
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 38…Qxf6 | Took the bishop that was bait for a royal fork | 5% → 3% | −1.77 |
| [07-14 17:37 (B)](../games/2026-07-14-17-37-maia-600-vs-guest.html) | 11…Kxd8 | One recapture walked into castling-with-check | 90% → 88% | −0.72 |
<!-- END TREND:EVIDENCE -->

**The habit to build:** treat every capture — *especially* recaptures — as a brand-new move. Ask: **"Why am I allowed to take this?"** If a full-strength opponent leaves something en prise, assume it's a deflection or attraction until you've checked every check and capture in reply. And after any exchange, re-scan which lines just opened (every pawn capture opens two lines — yours *and* theirs).

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/practice/fundamental-tactics/zwischenzug/ITWY4GN2/CSGoTH5f — **Practice: Zwischenzug** — the interactive lichess lesson on in-between moves: the direct cure for automatic recaptures.
2. https://lichess.org/training/intermezzo — Intermezzo puzzle trainer — endless reps of "the obvious recapture is wrong".
3. https://lichess.org/study/wHl4EGiN — *Zwischenzug (In-between moves) Puzzles* — themed puzzle set.
4. https://lichess.org/study/3BXFIMtX/l39o66lp — *Introduction to Intermezzo* — concept first, then exercises.
5. https://lichess.org/study/jV1A3RrM — *Intermediate: Tactics Internalized: Zwischenzug* — spaced-repetition style set.
6. https://lichess.org/study/YnxJYFKE — *Tactics — Zwischenzug (In-between move)* — more reps.
7. https://lichess.org/study/9ms9GmEU — *zwischenzug — in between moves* — more reps.
8. https://lichess.org/study/GcpdEPWF — *Lowell School: Tactic: Zwischenzug* — teaching set with explanations.
9. https://lichess.org/study/jcbJLf9B — *zwischenzug / jugada intermedia / intermezzo 1* — extra volume.
10. https://lichess.org/practice/intermediate-tactics/deflection/kdKpaYLW/h9gLa7uT — **Practice: Deflection** — learn the bait mechanism from the attacker's side so you recognize it when *you're* offered the gift (35.Qxb2 was a deflection victim).
11. https://lichess.org/practice/fundamental-tactics/overloaded-pieces/o734CNqp/YOva0EFV — **Practice: Overloaded Pieces** — teaches you to ask what a capturing piece *stops defending* (your queen on b2 stopped defending g2).
12. https://lichess.org/study/YbXWEP2N — *Intermediate: Tactics: Overloaded Piece* — same theme, exercise form.
13. https://lichess.org/training/capturingDefender — Capture the Defender trainer — trains the "what was that piece guarding?" reflex from the winning side.
14. https://lichess.org/training/defensiveMove — Defensive Move trainer — puzzles where the right move is the careful one, not the greedy one.

---

## 3. King safety — you open lines toward your own king

The 07-09 20:18 game is the textbook case: the engine had you **+3.5 out of a sleepy 1.e3 opening**, and 21…g5?? (pushing a pawn onto a square attacked twice, in front of your own castled-long king's flank) followed by 22…fxg5? opened the c1–h6 diagonal — one bishop then ate a pawn, a knight, a rook and finally your queen through that one diagonal. In the 12:11 game your king sat on c1 under a queenside pawn storm while you spent tempi grabbing the h5-pawn (26.Bxh5?, −3.6); the attack arrived first, and 24.bxa5?? even opened the b-file into your own king (mate in 5 against you). In the 07-11 game the king walked forward into the open (28…Kxf6) straight into a mating net.

<!-- TREND:EVIDENCE tags=king-safety,unsafe-king-move,pawn-break-timing -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 21…g5? | Pushed …g5 into the h4-pawn's teeth — with a bishop watching from c1 | 76% → 54% | −3.02 |
| [07-15 21:31 (W)](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | 33.Kd6?! | The king marched forward when its job was to walk home | 45% → 26% | −2.77 |
| [07-14 17:37 (B)](../games/2026-07-14-17-37-maia-600-vs-guest.html) | 4…e5?! | The centre break came a move before it was ready | 52% → 35% | −1.86 |
| [07-09 17:46 (W)](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | 11.Na3 | A tempo on the rim while the centre break waited | 78% → 71% | −1.24 |
| [07-15 21:31 (W)](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | 45.Ke3 | The king stepped onto the promotion diagonal — and made the deflection work | 5% → 2% | mate |
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 41…c4 | A pawn push on the wrong errand while the mating net closed | 2% → 2% | mate |
<!-- END TREND:EVIDENCE -->

**The habit to build:** the pawns in front of your king move only when you can name a concrete gain that outweighs the permanent weakness — and *never* while enemy pieces are aimed at that flank. When your king is under attack, material is irrelevant: count attackers vs. defenders around the king before counting pawns. (Note the asymmetry in your one won game as Black: the …g5/…g4 storm on 07-05 worked because *White's* king was stuck in the center and yours had the extra defender — the rule is about *your* king's coverage, not about pawn pushes in general.)

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/study/ukMqeI6m/rfwDiCe2 — *King safety* (FM Heineccius) — dedicated lesson on shelter, weakening pushes, and when they're justified.
2. https://lichess.org/study/VIykrfMP/stlQeErM — *Chess Strategy — King Safety* — concept-and-example study.
3. https://lichess.org/training/exposedKing — Exposed King trainer — punish exposed kings in puzzles until you feel *why* yours must not become one.
4. https://lichess.org/training/kingsideAttack — Kingside Attack trainer — see attacks from the attacker's side; the patterns that beat you (open diagonal, open file toward the king) repeat here endlessly.
5. https://lichess.org/practice/intermediate-tactics/greek-gift/s5pLU7Of/uCkLsFs1 — **Practice: Greek Gift** — the standard Bxh7+ sacrifice: the canonical punishment for a weakened king shelter; learn it from both sides.
6. https://lichess.org/study/Q7CWvKM0/iORv4Mxg — *Puzzles for defensive skills — series* — finding the defensive resource under attack.
7. https://lichess.org/study/rgSv9KtF — *Defensive tactics* — more defense-first puzzles.
8. https://lichess.org/study/5Ax6sL8x/3g4CSs7T — *defensive puzzles* — extra reps.
9. https://lichess.org/study/gzJKRPF1 — *defense from tactic puzzles* — extra reps.
10. https://lichess.org/training/defensiveMove — Defensive Move trainer (also listed in §2 — it's the bridge between both leaks).
11. https://lichess.org/@/datajunkie/blog/9-10-things-you-should-know-about-defending-against-an-attack-in-chess/pU3i3FkK — blog: *10 Things You Should Know About Defending Against An Attack* — checklist-style advice for exactly the 12:11-game situation.
12. https://lichess.org/forum/general-chess-discussion/when-to-push-the-pawns-infront-the-king?page=1 — forum thread: when pushing shelter pawns is and isn't justified — short and worth reading once.
13. https://lichess.org/@/Kingscrusher-YouTube/blog/the-complete-guide-to-chess-opening-principles-king-safety-driven-development/5zEb9Utr — blog: king-safety-driven development — ties this section to §6.

---

## 4. You don't hunt forcing moves — mates and perpetuals sail past

This one is stark in the data. Across the seven games you missed:

<!-- TREND:EVIDENCE tags=missed-mate,slow-mate,missed-tactic -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-09 12:11 (W)](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | 29.Qg4?? | You had a draw on f7 and never looked for it | 50% → 4% | −8.84 |
| [07-13 18:31 (W)](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | 10.Nb7?? | b7: one square in, no squares out | 70% → 27% | −5.09 |
| [07-05 14:50 (B)](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | 9…Nd7?? | Backed away from a pawn tension you were winning | 70% → 36% | −3.73 |
| [07-11 15:49 (B)](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | 23…Qd7? | Fourth invitation declined — and the knight finally fell | 86% → 59% | −3.92 |
| [07-11 15:49 (B)](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | 17…Bh8? | Retreated to the corner with the door hanging off its hinges | 84% → 57% | −4.42 |
| [07-09 17:46 (W)](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | 4.e5?! | Pushed past a pawn that was free to take | 73% → 59% | −1.64 |
| [07-06 19:53 (W)](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) | 52.Qe3 | Offered a queen trade when you could just win the queen | 98% → 89% | mate lost |
| [07-15 21:31 (W)](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | 12.d5 | The center push released the pressure — the capture won a pawn | 57% → 50% | −0.86 |
| [07-05 14:50 (B)](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | 36…Ra2 | Three checks from the finish line, you looked away | 98% → 98% | missed #3 |
| [07-09 17:46 (W)](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | 34.Qc6+ | Mate in one — missed twice | 98% → 98% | missed #1 |
| [07-14 17:37 (B)](../games/2026-07-14-17-37-maia-600-vs-guest.html) | 50…Qa1+ | Mate in one, promoted two moves late | 98% → 98% | missed #1 |
<!-- END TREND:EVIDENCE -->

Two skills are missing, and they're the same skill pointed in opposite directions: **when winning, check every check before every quiet move; when losing, hunt for the perpetual first.** You have the patterns (you *did* mate cleanly in two games) — you're just not *scanning* for forcing moves systematically.

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/practice/checkmates/checkmate-patterns-i/fE4k21MW/9rd7XwOw — **Practice: Checkmate Patterns I** — the named mates; makes mates-in-one leap off the board at you.
2. https://lichess.org/practice/checkmates/checkmate-patterns-ii/8yadFPpU/UZ1np9Is — **Practice: Checkmate Patterns II**.
3. https://lichess.org/practice/checkmates/checkmate-patterns-iii/PDkQDt6u/ygAaFQNc — **Practice: Checkmate Patterns III**.
4. https://lichess.org/practice/checkmates/checkmate-patterns-iv/96Lij7wH/qr2pOlrL — **Practice: Checkmate Patterns IV**.
5. https://lichess.org/training/mateIn1 — Mate-in-1 trainer. You walked past two of these outright (and a stack of mates-in-two); drill until they're instant.
6. https://lichess.org/training/mateIn2 — Mate-in-2 trainer — the natural next step; forces the "every check, every reply" scan.
7. https://lichess.org/training/mateIn3 — Mate-in-3 trainer — builds the short forced-line calculation you needed in the 07-06 game.
8. https://lichess.org/study/dxVT98YD/zEGPySfm — *Checks, Captures, Threats* — the move-selection ritual itself, as a study.
9. https://lichess.org/study/wmi4cpQp — *How to Create a Plan — Look for Checks, Captures and Threats* — same ritual, applied.
10. https://lichess.org/video/K_-Yt2NxTU4 — video: *Checks, Captures & Threats Method* (IM Alex Astaneh) — 20 minutes, watch once, apply forever.
11. https://lichess.org/study/EHA5Q06S/0sLfdLQ1 — *Mate in 1, 2, & 3 for Beginners* — graded single set.
12. https://lichess.org/study/IjkwOT5e/MLmQWH9y — *Exercises: Mate in one (part 1)* — volume reps.
13. https://lichess.org/study/iixBtBrI/pup7ytLV — *Mate in two moves. Exercises* (IM Monkey_King) — quality mate-in-2 set.
14. https://lichess.org/study/c7EwKyMy/XxG8wpEB — *5334: Mate in Two Part 1* — the classic Polgár exercises on lichess.
15. https://lichess.org/study/hqmSoiYO/0LsmqxWW — *Tricky mates in two* — for when the easy ones get automatic.
16. https://lichess.org/study/4Re4Lmxw — *Mating Puzzles (mate in 2)* — extra volume.
17. https://lichess.org/study/mAAzSuxx — *Mate in 1 puzzles (plus 2s and 3s)* — extra volume.
18. https://lichess.org/study/F3AllbNb/W5S7x1Io — *Mate in 1, 2 and 3 puzzles from games* — real-game finishes.
19. https://lichess.org/study/JrwLZArS/j8tRCe9Y — *Mate in 3 puzzles!* — extra volume.
20. https://lichess.org/study/FfDCg0XR/hChsuTPx — *Mate in 3 or 4 Puzzles* — stretch goal.
21. https://lichess.org/study/5u5tXlKg/U7nGvhke — *All 30 Checkmate Patterns* — compact pattern reference.
22. https://lichess.org/training/backRankMate — Back-Rank Mate trainer — the most common missed-mate family.
23. https://lichess.org/study/oYmEsHwe/LeCCwfHJ — *Back Rank Mate Puzzles* — themed set.
24. https://lichess.org/study/uqztxD5h — *Back-Rank Mate: Everything about it* — lesson + exercises.
25. https://lichess.org/study/jOsMvS68/zHxSLTyY — *Perpetual check. Exercises* (IM Monkey_King) — **the half-point you left on the table in the 12:11 game.**
26. https://lichess.org/study/aPrv1yVQ — *Perpetual check. Theory* (IM Monkey_King) — read before the exercises.
27. https://lichess.org/study/feh6YY6d — *Stalemate, Perpetual check, Threefold repetition* — all the escape hatches in one study.
28. https://lichess.org/study/OHUEkGUK — *drawing completely lost positions* — the "when losing, hunt the draw" mindset.
29. https://lichess.org/study/A0DQmBKQ — *Calculation (finding candidate moves)* — forcing-moves-first candidate generation.
30. https://lichess.org/study/Ux6HeaNm — *Calculation training, forcing moves* — reps.
31. https://lichess.org/study/vhGnR8d7 — *calculation exercises* — reps.
32. https://lichess.org/study/jftL3ptX/V4MDO20I — *Visualization Exercises* — you can only calculate as deep as you can visualize.
33. https://lichess.org/streak — Puzzle Streak — untimed, escalating difficulty; great daily forcing-move scan practice.
34. https://lichess.org/storm — Puzzle Storm — timed pattern-speed builder (use sparingly; speed is not your bottleneck).

---

## 5. Converting winning positions — the +5 that becomes 0

The outcome-level leak that the previous categories feed. The record across these seven games:

<!-- TREND:EVIDENCE tags=conversion-drift,endgame-technique,promotion-race -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-06 19:53 (W)](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) | 63.g3?? | Shuffled a pawn while your king sat idle | 88% → 50% | −7.05 |
| [07-15 21:31 (W)](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | 25.Rd6?? | One rook move gave the whole piece back | 85% → 50% | −4.80 |
| [07-13 18:31 (W)](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | 15.Qd3?! | The queen stepped into the c-pawn's headlights | 88% → 71% | −3.19 |
| [07-09 17:46 (W)](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | 25.Qa3 | The a1-rook never joined the game | 93% → 90% | −1.69 |
| [07-14 17:37 (B)](../games/2026-07-14-17-37-maia-600-vs-guest.html) | 28…g6 | The king had an escort job — you sent the g-pawn instead | 98% → 95% | −2.80 |
<!-- END TREND:EVIDENCE -->

Three sub-habits are missing:

- **Open lines / strike when winning.** In 07-11 the engine wanted the central break …exf3 for ten straight moves while you shuffled. Winning positions are converted by opening lines for the extra material, not by avoiding contact.
- **When winning, get paranoid, not casual.** The blunders above all came *after* the position was won — the most dangerous moment in chess. Solve your opponent's threat first (prophylaxis), then push.
- **Endgame technique.** 07-06 ended in a completely won B+N+passed-pawn endgame that dissolved in four moves.

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/study/I9YbUAV8/E66o3Reg — *How to Win Winning Positions* (IM TheHeartofChess) — exactly this problem, chapter by chapter.
2. https://lichess.org/study/Wu6O6k7m — *Technique — Converting an Advantage / Maximising* — practical conversion technique.
3. https://lichess.org/training/advantage — Advantage trainer — puzzles where the reward is a winning (not mating) position, then you must keep it.
4. https://lichess.org/training/crushing — Crushing trainer — spot the blunder, get a ≥+6 position — trains the "stay sharp when it's already won" muscle.
5. https://lichess.org/study/UXVPcUOZ/08mdRZK5 — *Prophylaxis exercises* (FM JosePadeiro) — "what does my opponent want?" — the question that saves won games.
6. https://lichess.org/study/SNWKXWlk — *Prophylaxis Puzzles* — more reps.
7. https://lichess.org/study/TypmFAbe/YfCXBlz6 — *Prophylaxis in Chess Middlegames* — concept study.
8. https://lichess.org/study/vOEUBDcg — *Chess Strategy — Prophylaxis* — alternative presentation.
9. https://lichess.org/study/JlvrbfQn — *Simplification — Part 1* — trade pieces, not pawns, when ahead.
10. https://lichess.org/study/zznJhuGd — *SIMPLIFICATION* — more examples.
11. https://lichess.org/study/2HHBEEqT — *When to trade or not to trade pieces* — the decision rules.
12. https://lichess.org/practice/checkmates/piece-checkmates-i/BJy6fEDf/8K8FdT6P — **Practice: Piece Checkmates I** — K+Q and K+R vs K until they're reflexes; converting means finishing.
13. https://lichess.org/study/zNsUmoVY — *Queen or Rook vs King Exercises* — basic mate delivery reps.
14. https://lichess.org/study/opgcgude — *Checkmate with the Rook and King* — technique study.
15. https://lichess.org/practice/pawn-endgames/key-squares/xebrDvFe/o3Hq4RZ0 — **Practice: Key Squares** — the pawn-endgame foundation for cashing in extra material.
16. https://lichess.org/study/7w5GUwhT — *Practice: King and Pawn Endgames I* — guided pawn-endgame module.
17. https://lichess.org/study/dqCpuvFS/eQLYGkny — *Practice: Rook And Pawn Endgames* — Lucena/Philidor and friends.
18. https://lichess.org/training/rookEndgame — Rook Endgame trainer — practical endgame puzzles.
19. https://lichess.org/study/aJa70P5N — *Promoting Pawns Study* — escorting the passer (your b-pawn and a-pawn games show you like passers — finish them cleanly).
20. https://lichess.org/study/L8k6PKMU — *Common Endgame Tactics #2: Passed Pawn Odyssey* — passed-pawn tactics.
21. https://lichess.org/study/xy2UDdiU — *Endgame Technique: Create passed pawn by winning pawns* — building the passer.
22. https://lichess.org/training/promotion — Promotion trainer — promotion tactics.
23. https://lichess.org/training/advancedPawn — Advanced Pawn trainer — the 7th-rank pawn tactics family.
24. https://lichess.org/study/sr5b6mnr — *2 queens: how to prevent stalemate* — you've now had two two-queen games; this 5-minute study prevents the classic accident.
25. https://lichess.org/study/JgB4zdIz — *Stalemate Practice* — the other half of that insurance.
26. https://lichess.org/forum/general-chess-discussion/how-to-improve-in-converting-winning-positions — forum thread: converting advice from stronger players.
27. https://lichess.org/forum/general-chess-discussion/unable-to-convert-clearly-winning-positions-how-do-i-improve — forum thread: same topic, more angles.

---

## 6. Opening habits — adventures before development

The least costly category in eval terms, but it set up several of the disasters above. Recurring items:

<!-- TREND:EVIDENCE tags=opening-principle -->
| Game | Move | What happened | Your win% | Cost |
|---|---|---|---|---|
| [07-05 14:50 (B)](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | 6…Nb4? | A one-move threat that abandoned the e5-pawn | 58% → 34% | −2.74 |
| [07-09 20:18 (B)](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | 9…Nb5?! | Retreated a monster knight that nobody was attacking | 67% → 50% | −1.74 |
| [07-09 12:11 (W)](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | 12.Na4?! | Sent the knight to the rim, where it became a target | 51% → 36% | −1.58 |
| [07-09 12:11 (W)](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | 8.Qg4?! | The queen went adventuring before the pieces were out | 56% → 45% | −1.31 |
<!-- END TREND:EVIDENCE -->

**The habit to build:** in the first 10–12 moves — develop a new piece each move toward the center, castle before starting operations, don't move the queen out early, don't move the same piece twice without a concrete reason, and *always* check whether a central capture is simply free. Before any knight jump, count its retreat squares: zero means it's lost.

**Lichess studies & exercises (most impactful first):**

1. https://lichess.org/study/vyS3PnUA/h8sUGQ2Z — *Opening Principles And Theory — Learning Lesson* — the principles, interactive.
2. https://lichess.org/study/393yZ8hJ — *Starting Out a Chess Game: Opening Principles!* — same ground, different examples.
3. https://lichess.org/study/ZTYzV6Jl — *Basic opening principles* — compact version.
4. https://lichess.org/study/NfMygq6x/cncxKfyw — *An Introduction to Opening Theory* — why the principles exist.
5. https://lichess.org/video/kURU67G98O8 — video: *Chess Basics: Opening Principles*.
6. https://lichess.org/training/opening — Opening-phase puzzle trainer — punish opening mistakes (including early queen sorties) tactically.
7. https://lichess.org/study/Okg4LOJB/xYH86iCY — *Trapping Pieces EXERCISE* — the b7-knight lesson, from the trapping side: learn which squares are traps.
8. https://lichess.org/study/PksUBvjS/7qnQPUG8 — *Trapping pieces* — more trap patterns.
9. https://lichess.org/training/trappedPiece — Trapped Piece trainer — spot doomed pieces (before you create one).
10. https://lichess.org/study/zti5dtmO — *Knight trapped* — knight-specific trap patterns.
11. https://lichess.org/study/CI2zREac — *Two trapped knights* — more of the same.
12. https://lichess.org/study/YoGTjm0V — *Annoying Queens! Stopping Early Queen Attacks* (GothamChess study) — you played 8.Qg4 yourself; seeing why early queens fail cures both sides of the habit.
13. https://lichess.org/study/9Ui9ETCY/64DQ9kdG — *Defending early queen attacks* — the defensive side.
14. https://lichess.org/study/Pk8uFkMs — *6 Proven Tips to PUNISH Early Queen Attacks* — checklist form.
15. https://lichess.org/study/N4ikSIua — *Punish the Wayward Queen attack* — concrete refutation lines.
16. https://lichess.org/study/y39Fw5Bf — *How to Punish Early Queen Attacks!* — extra examples.
17. https://lichess.org/study/VejXPPZv/S9DqzF09 — *Wayward Queen Attack* — know the trap everyone plays at club level.
18. https://lichess.org/@/Kingscrusher-YouTube/blog/the-complete-guide-to-chess-opening-principles-king-safety-driven-development/5zEb9Utr — blog: opening principles framed around king safety.

---

## Other advice worth more than any single study

### The 5-second pre-move ritual (fixes §1, §2, §4 at once)

Before *releasing* every move, in this order:

1. **Checks** — every check for both sides. (Would have found five mates-in-one and two perpetuals.)
2. **Captures** — every capture for both sides, *including replies to your intended move*. ("Why am I allowed to take this?")
3. **Landing square** — count enemy attackers of the square your piece is going to, *including sleeping long-range pieces behind blockers*.
4. **Leaving square** — what did the moving piece defend?

This is the entire fix for perhaps 80% of the eval you lost in these seven games. It costs a few seconds per move — which is also why the next point matters.

### Play time controls that allow the ritual

These were classical games, good. Keep playing 15+10 or slower while the ritual becomes automatic. Blitz will re-teach the autopilot recapture you're trying to unlearn.

### Change your sparring partner

Five of these games were against full-strength Stockfish, which punishes perfectly but plays inhumanly — you learn fear, not patterns. Level 3 is better but gives absurd gifts (you saw 3.c5?? and 5.b4??), which trains bad habits too. The sweet spot on Lichess:

- **Maia bots** — neural nets trained to play like humans at specific ratings: https://lichess.org/@/maia1 (~1100-level), https://lichess.org/@/maia5 (~1500), https://lichess.org/@/maia9 (~1900). They blunder like humans, so punishing them trains exactly the §1 skills. (Team page: https://lichess.org/team/maia-bots)
- **Rated human games** — the real feedback loop.

### Make the engine review a routine, not an event

After every game: run the Lichess server analysis and click **"Learn from your mistakes"** in the analysis screen — it replays your errors and makes you find the right move. Then, for games that deserve it, keep doing what you're doing with this repo — the coach pages in `games/` are a genuinely good spaced-repetition source. Re-open old pages weekly and re-answer each mistake card before reading the explanation.

### A 30-minute daily plan built from your actual weaknesses

| Day | Drill (≈30 min) |
|---|---|
| Mon | 10× https://lichess.org/training/hangingPiece + 10× https://lichess.org/training/mateIn1 |
| Tue | One chapter of a §2 zwischenzug study + 10× https://lichess.org/training/intermezzo |
| Wed | 10× https://lichess.org/training/mateIn2 + one §4 CCT chapter |
| Thu | One chapter of *How to Win Winning Positions* (§5) + 10× https://lichess.org/training/advantage |
| Fri | 10× https://lichess.org/training/defensiveMove + one §3 king-safety chapter |
| Sat | One slow game (15+10 or slower) vs a Maia bot or human, ritual on every move, then "Learn from your mistakes" |
| Sun | https://lichess.org/training/dashboard — review the week; retry every failed puzzle; one https://lichess.org/streak run |

Track weaknesses over time with the **Puzzle Dashboard** (https://lichess.org/training/dashboard) — after a few hundred puzzles it will show your themes objectively; expect *Hanging Piece*, *Defensive Move* and *Mate in 1* to be the low bars at first. Browse all themes at https://lichess.org/training/themes, and use https://lichess.org/training/mix for a healthy default. The full guided-lesson catalog is at https://lichess.org/practice, and https://lichess.org/learn covers fundamentals if you ever want a refresher.

### One encouraging pattern in the data

Your two wins were the two games with the lowest average eval loss (39 and 63 cp/move) — when you're careful, you're already strong enough to beat these opponents. The queenside play in the 07-05 game (…a5, …axb4, the b-pawn promotion) and the space-grabbing setups you get as White show real positional instinct. Nothing in these seven games suggests you need more chess *knowledge* — they all point at the same 5-second discipline gap, and that's fixable with reps.

---

## Methodology

Every position where you were to move was analyzed with **Stockfish 16 at depth 20** (the same engine/depth used for the per-game coach pages): eval before the move, engine's best move and its eval, eval after your actual move. "Cost" figures are the difference between your move and the engine's best, from your perspective; `#N` means forced mate in N. Mistake selection threshold: ≥1.00 eval loss, plus all missed/allowed forced mates. Player color per game was taken from the PGN headers (`White`/`Black` = "Anonymous"; the 2026-07-11 file's headers name White as "Stockfish-level-3", so you were Black despite the filename).

## Sources used for this report

<!-- TREND:SOURCES -->
| # | Source PGN (pgn/) | Coach page (games/) | You played | Result |
|---|---|---|---|---|
| 1 | [2026-07-05-14-50-stockfish-vs-anonymous.txt](../pgn/2026-07-05-14-50-stockfish-vs-anonymous.txt) | [2026-07-05-14-50-stockfish-vs-anonymous.html](../games/2026-07-05-14-50-stockfish-vs-anonymous.html) | Black | 0–1 (won) |
| 2 | [2026-07-06-19-53-anonymous-vs-stockfish.txt](../pgn/2026-07-06-19-53-anonymous-vs-stockfish.txt) | [2026-07-06-19-53-anonymous-vs-stockfish.html](../games/2026-07-06-19-53-anonymous-vs-stockfish.html) | White | 0–1 (lost) |
| 3 | [2026-07-09-12-11-anonymous-vs-stockfish.txt](../pgn/2026-07-09-12-11-anonymous-vs-stockfish.txt) | [2026-07-09-12-11-anonymous-vs-stockfish.html](../games/2026-07-09-12-11-anonymous-vs-stockfish.html) | White | 0–1 (lost) |
| 4 | [2026-07-09-17-46-anonymous-vs-stockfish.txt](../pgn/2026-07-09-17-46-anonymous-vs-stockfish.txt) | [2026-07-09-17-46-anonymous-vs-stockfish.html](../games/2026-07-09-17-46-anonymous-vs-stockfish.html) | White | 1–0 (won) |
| 5 | [2026-07-09-20-18-stockfish-vs-anonymous.txt](../pgn/2026-07-09-20-18-stockfish-vs-anonymous.txt) | [2026-07-09-20-18-stockfish-vs-anonymous.html](../games/2026-07-09-20-18-stockfish-vs-anonymous.html) | Black | 1–0 (lost) |
| 6 | [2026-07-11-15-49-anonymous-vs-anonymous.txt](../pgn/2026-07-11-15-49-anonymous-vs-anonymous.txt) | [2026-07-11-15-49-anonymous-vs-anonymous.html](../games/2026-07-11-15-49-anonymous-vs-anonymous.html) | Black | 1–0 (lost) |
| 7 | [2026-07-13-18-31-anonymous-vs-stockfish-level-3.txt](../pgn/2026-07-13-18-31-anonymous-vs-stockfish-level-3.txt) | [2026-07-13-18-31-anonymous-vs-stockfish-level-3.html](../games/2026-07-13-18-31-anonymous-vs-stockfish-level-3.html) | White | 0–1 (lost) |
| 8 | [2026-07-14-17-37-maia-600-vs-guest.txt](../pgn/2026-07-14-17-37-maia-600-vs-guest.txt) | [2026-07-14-17-37-maia-600-vs-guest.html](../games/2026-07-14-17-37-maia-600-vs-guest.html) | Black | 0–1 (won) |
| 9 | [2026-07-15-21-31-emgosr-vs-maia-800.txt](../pgn/2026-07-15-21-31-emgosr-vs-maia-800.txt) | [2026-07-15-21-31-emgosr-vs-maia-800.html](../games/2026-07-15-21-31-emgosr-vs-maia-800.html) | White | 0–1 (lost) |
<!-- END TREND:SOURCES -->
