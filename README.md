# chess-puzzles

A **chess puzzle trainer with a real engine** in **pure Python** — no dependencies.

What started as 7 hand-picked mate-in-1 puzzles is now a full puzzle
engine: it **generates** mate-in-2 and mate-in-3 positions and **proves**
every solution by search before you ever see it.

## Run it

```bash
python3 puzzles.py
```

Pick a mode from the menu:

| Mode | What it is |
|---|---|
| `1` classic mate-in-1 | the original 7 hand-picked puzzles |
| `2` mate-in-2 trainer | engine-generated, search-verified |
| `3` mate-in-3 trainer | engine-generated, search-verified |
| `4` streak mode | 3 lives — solve to build a streak, harder puzzles score more |
| `5` blitz mode | 150 seconds on the clock, points for speed and difficulty |

Type your move (like `Re8` or `Qxg7#`), ask for a `hint`, type `show`
to reveal the answer, or `quit` any time.

## The engine (`chess.py`)

A complete little chess engine, standard library only:

- **Full legal move generation** — castling, en passant, promotion,
  check / checkmate / stalemate detection. Validated against known
  perft counts (start position: 20 / 400 / 8902 / 197281 nodes).
- **`forced_mate(pos, depth)`** — proof search: a key move only counts if
  *every* black reply still loses. Mate-in-1 tries checking moves only;
  deeper mates recurse over all defenses.
- **SAN notation** with disambiguation, `+`/`#` suffixes, castling as
  `O-O` / `O-O-O`; FEN parsing and generation.

## Puzzle generation (`generate.py`)

```bash
python3 generate.py [seed]
```

Samples random endgame positions (KQ / KRR vs K, plus pawn blockers),
then keeps a position only if the engine **proves** a forced mate in
exactly N — and proves no faster mate exists. Each kept puzzle stores
its key move(s), a sample forced line, and a demo line for the video.
Results are re-verified from the FEN and saved to `generated.json`
(6× mate-in-2, 4× mate-in-3 with the default seed).

## Difficulty rating

Every generated puzzle gets 1–5 stars from real search data:

- **mate distance** — mate-in-3 starts harder than mate-in-2
- **branching** — how many legal moves you choose from
- **defenses** — how many black replies the key move must survive
- **quiet keys** — a non-check, non-capture key move is sneakier

## Hints & scoring

- `hint` once → reveals the **key piece** ("the key move is with the Rook")
- `hint` again → reveals the **key square** ("…to the square c4")
- Streak mode: 3 lives, points scale with puzzle stars
- Blitz mode: 150 seconds, `100 + 25 × stars` per solve

## Try changing

- Add your own mate-in-1 puzzles: append a
  `{"name", "fen", "solution", "tip"}` dict to `PUZZLES` in `puzzles.py`.
- Generate a fresh puzzle set with a new seed: `python3 generate.py 42`.
- Ask for mate-in-4: `forced_mate` already supports any depth —
  generation just gets slower (that's the fun of search).

Built by [Mohammad Ali](https://github.com/AliRender13).

## In the wild

- 🎥 [Code walkthrough video on LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7511664513130258432/) — the chess engine proving forced mates, generating verified puzzles, and the trainer's streak & blitz modes in action.
