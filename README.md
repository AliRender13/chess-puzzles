# chess-puzzles

A **mate-in-one chess puzzle trainer** in **pure Python** — no dependencies.

## Run it

```bash
python3 puzzles.py
```

White is to move and checkmate in one. Type your move (like `Re8`),
ask for a `hint`, or `quit` any time. 7 hand-picked puzzles, score at the end.

## What's inside

- 7 famous mating patterns (back-rank mates, queen sacrifices, rook
  corridors) stored as FEN strings.
- A tiny FEN parser that draws each position as an ASCII board — no chess
  library needed.
- Forgiving answer checking: `Re8`, `re8#` and `RE8+` all count.

## Try changing

- Add your own puzzles: append a `{"name", "fen", "solution", "tip"}`
  dict to `PUZZLES`.
- Shuffle the deck with `random.shuffle(PUZZLES)` for replay value.

Built by [Mohammad Ali](https://github.com/AliRender13).
