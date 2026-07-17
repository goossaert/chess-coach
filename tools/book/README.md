# tools/book — offline Polyglot opening book

`gm2001.bin` powers the offline "left theory" detection for the opening
report (CLAUDE.md workflow step 3b): python-chess replays the game against
the book (`chess.polyglot.open_reader`) and the first ply with no book entry
is `bookExitPly`.

Provenance:

- Source: `https://raw.githubusercontent.com/michaeldv/donna_opening_books/master/gm2001.bin`
  (the opening-book collection shipped with the open-source Donna chess
  engine), retrieved 2026-07-17 through the sandbox proxy.
- Size 486,656 bytes · sha256 `fb6e9f3f27bb19a5b2fdefcc441c88ddeae48db61d5f00ad83973abb9f939c87`.
- "GM2001" is the widely redistributed freeware book compiled from
  grandmaster games (it ships with many free chess programs). The source
  repository carries no license file; the book is kept here as move-frequency
  data for offline lookup only.

Sanity check (weights are real game frequencies, not the flat weights of
tiny test books):

```
/tmp/chess-venv/bin/python -c "import chess, chess.polyglot; \
  r = chess.polyglot.open_reader('tools/book/gm2001.bin'); \
  print([(e.move.uci(), e.weight) for e in r.find_all(chess.Board())][:4])"
# [('e2e4', 10439), ('d2d4', 10366), ('g1f3', 2146), ('c2c4', 1645)]
```
