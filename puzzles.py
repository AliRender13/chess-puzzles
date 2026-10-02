"""
chess-puzzles — a chess puzzle trainer with a real engine, in pure Python.

- Classic mate-in-1 trainer (7 hand-picked puzzles)
- Mate-in-2 and mate-in-3 puzzles *generated* by the engine and *proven*
  by search: every puzzle's solution is verified, not trusted
- Difficulty stars, hint system, streak mode, timed blitz mode
- ASCII boards for puzzles and full solution playback

Run:
    python3 puzzles.py
"""
import json
import os
import random
import time

from chess import (parse_fen, to_san, legal_moves, make, unmake, in_check,
                   is_checkmate, is_stalemate, forced_mate, square_name,
                   PIECE_NAMES, opp)

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Classic mate-in-1 set (kept from the original trainer)
# --------------------------------------------------------------------------

PUZZLES = [
    {
        "name": "Back-Rank Basics",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
        "solution": ["RE8"],
        "tip": "The black king is trapped by its own pawns.",
    },
    {
        "name": "Queen Takes All",
        "fen": "6k1/5ppp/7B/8/8/8/1Q3PPP/6K1 w - - 0 1",
        "solution": ["QXG7"],
        "tip": "A sacrifice the king cannot refuse.",
    },
    {
        "name": "King Hunt",
        "fen": "7k/8/6K1/8/8/8/8/4R3 w - - 0 1",
        "solution": ["RE8"],
        "tip": "Cut off every escape square.",
    },
    {
        "name": "Queen's Corridor",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1",
        "solution": ["QD8"],
        "tip": "The long way round is the only way in.",
    },
    {
        "name": "Rook to the Corner",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        "solution": ["RA8"],
        "tip": "From the corner, the rook sees everything.",
    },
    {
        "name": "Queen's Highway",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/4Q1K1 w - - 0 1",
        "solution": ["QE8"],
        "tip": "Straight down the e-file.",
    },
    {
        "name": "Capturing the Defender",
        "fen": "3r2k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
        "solution": ["RXD8"],
        "tip": "Take the rook, take the game.",
    },
]


def show(board):
    print("  +-----------------+")
    for i, row in enumerate(board):
        print(f"{8 - i} | {' '.join(row)} |")
    print("  +-----------------+")
    print("    a b c d e f g h")


def normalise(move):
    return move.strip().upper().replace("#", "").replace("+", "").replace(" ", "")


def load_generated():
    path = os.path.join(HERE, "generated.json")
    if not os.path.exists(path):
        return {"mate_in_2": [], "mate_in_3": []}
    with open(path) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Move matching / answer checking against the engine
# --------------------------------------------------------------------------

def san_options(pos):
    """normalized SAN -> move, for every legal move (forgiving variants)."""
    opts = {}
    for m in legal_moves(pos):
        san = to_san(pos, m)
        base = normalise(san)
        opts[base] = m
        opts[base.replace("X", "")] = m
        for suffix in ("=Q", "=R", "=B", "=N"):
            if suffix in base:
                opts[base.replace(suffix, "")] = m
    # castling long forms
    for m in legal_moves(pos):
        if abs(m[3] - m[1]) == 2 and pos.board[m[0]][m[1]].upper() == "K":
            opts["O-O" if m[3] == 6 else "O-O-O"] = m
            opts["0-0" if m[3] == 6 else "0-0-0"] = m
    return opts


def match_move(pos, text):
    return san_options(pos).get(normalise(text))


def match_stored_san(pos, san):
    """Find the legal move whose SAN equals a stored SAN (for playback)."""
    for m in legal_moves(pos):
        if to_san(pos, m) == san:
            return m
    # fallback: square match
    return None


# --------------------------------------------------------------------------
# Hints
# --------------------------------------------------------------------------

def hint_text(puzzle, level, depth):
    """level 1: key piece · level 2: key square."""
    if depth == 1:
        sol = puzzle["solution"][0]
        piece = PIECE_NAMES.get(sol[0], sol[0])
        sq = sol[-2:]
        if level == 1:
            return f"hint: {puzzle['tip']}"
        return f"hint: the key move lands on {sq.lower()}."
    if level == 1:
        return f"hint: the key move is with the {puzzle['hint_piece']}."
    return f"hint: …to the square {puzzle['hint_square']}."


# --------------------------------------------------------------------------
# Solution playback
# --------------------------------------------------------------------------

def play_line(fen, line):
    """Replay a forced line on ASCII boards, move by move."""
    pos = parse_fen(fen)
    show(pos.board)
    for i, info in enumerate(line):
        m = match_stored_san(pos, info["san"])
        if m is None:
            print(f"  (could not replay {info['san']})")
            return
        num = i // 2 + 1
        tag = f"{num}. {info['san']}" if i % 2 == 0 else f"{num}... {info['san']}"
        print(f"\n  {tag}")
        make(pos, m)
        show(pos.board)
    print("\n  ♛  CHECKMATE — every defense leads here.\n")


# --------------------------------------------------------------------------
# One puzzle round (quiz the key move)
# --------------------------------------------------------------------------

def ask_puzzle(puzzle, depth, num, total, deadline=None):
    """Quiz one puzzle. Returns (solved, hints_used, timed_out)."""
    stars = "★" * puzzle.get("stars", 1) if depth > 1 else "★"
    print(f"--- Puzzle {num}/{total}: {puzzle['name']} {stars} ---")
    print(f"    White to move — mate in {depth}.")
    pos = parse_fen(puzzle["fen"])
    show(pos.board)
    hints = 0
    while True:
        if deadline is not None and time.time() > deadline:
            return False, hints, True
        try:
            ans = input("your move (or 'hint' / 'show' / 'quit'): ")
        except (EOFError, KeyboardInterrupt):
            print()
            return False, hints, False
        cmd = normalise(ans)
        if cmd == "QUIT":
            return None, hints, False
        if cmd == "HINT":
            hints += 1
            print(hint_text(puzzle, min(hints, 2), depth))
            continue
        if cmd == "SHOW":
            print(f"answer: {puzzle['keys'][0] if depth > 1 else puzzle['solution'][0]}")
            if depth > 1 and puzzle.get("demo"):
                play_line(puzzle["fen"], puzzle["demo"])
            return False, hints, False
        if depth == 1:
            ok = cmd in puzzle["solution"]
        else:
            m = match_move(pos, ans)
            ok = m is not None and any(
                normalise(k) == normalise(to_san(pos, m).replace("+", "").replace("#", ""))
                for k in puzzle["keys"])
        if ok:
            print("correct! that's the key move.\n")
            return True, hints, False
        print("not quite — try again (or type 'hint').")


def quiz_list(puzzles, depth, title):
    score = 0
    random.shuffle(puzzles)
    for n, p in enumerate(puzzles, 1):
        res, _, _ = ask_puzzle(p, depth, n, len(puzzles))
        if res is None:
            break
        if res:
            score += 1
            if depth > 1 and p.get("demo"):
                play_line(p["fen"], p["demo"])
    print(f"done! final score: {score}/{len(puzzles)}")


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def mode_classic():
    print("\n♞  Classic mate-in-1 — White to move and checkmate.\n")
    quiz_list(list(PUZZLES), 1, "classic")


def mode_depth(depth, gen):
    key = "mate_in_2" if depth == 2 else "mate_in_3"
    puzzles = gen.get(key, [])
    if not puzzles:
        print("no generated puzzles found — run: python3 generate.py")
        return
    print(f"\n♞  Mate-in-{depth} trainer — positions generated by the engine,")
    print("   every solution *proven* by search. Find the key move.\n")
    quiz_list(list(puzzles), depth, f"mate-in-{depth}")


def all_puzzles(gen):
    pool = []
    for p in PUZZLES:
        pool.append((1, dict(p, stars=1)))
    for p in gen.get("mate_in_2", []):
        pool.append((2, p))
    for p in gen.get("mate_in_3", []):
        pool.append((3, p))
    return pool


def mode_streak(gen):
    pool = all_puzzles(gen)
    random.shuffle(pool)
    lives, streak, best, score = 3, 0, 0, 0
    print("\n♞  Streak mode — 3 lives. Solve to build the streak,")
    print("   wrong key moves cost a life. Harder puzzles score more.\n")
    i = 0
    while lives > 0 and pool:
        depth, p = pool[i % len(pool)]
        i += 1
        res, _, _ = ask_puzzle(p, depth, streak + 1, "∞")
        if res is None:
            break
        if res:
            streak += 1
            best = max(best, streak)
            pts = 10 * p.get("stars", 1)
            score += pts
            print(f"  streak {streak} (+{pts} pts, best {best})\n")
            if depth > 1 and p.get("demo"):
                play_line(p["fen"], p["demo"])
        else:
            lives -= 1
            streak = 0
            print(f"  ✗ the key was {p['keys'][0] if depth > 1 else p['solution'][0]}"
                  f" — {lives} {'life' if lives == 1 else 'lives'} left.\n")
    print(f"game over! best streak {best}, final score {score}")


def mode_blitz(gen, seconds=150):
    pool = all_puzzles(gen)
    deadline = time.time() + seconds
    solved, score = 0, 0
    print(f"\n♞  Blitz mode — {seconds} seconds on the clock. Go!\n")
    n = 0
    while time.time() < deadline and pool:
        n += 1
        depth, p = random.choice(pool)
        left = int(deadline - time.time())
        print(f"  ⏱ {left}s left")
        res, _, timed_out = ask_puzzle(p, depth, n, "blitz", deadline)
        if timed_out or res is None:
            break
        if res:
            solved += 1
            pts = 100 + 25 * p.get("stars", 1)
            score += pts
            print(f"  +{pts} pts\n")
    print(f"time! solved {solved} puzzles — final score {score}")


def main():
    gen = load_generated()
    n2, n3 = len(gen.get("mate_in_2", [])), len(gen.get("mate_in_3", []))
    print("♞  chess-puzzles — now with a real engine")
    print("   mate-in-2 & mate-in-3 puzzles proven by search\n")
    while True:
        print("  1) classic mate-in-1      (7 puzzles)")
        print(f"  2) mate-in-2 trainer       ({n2} engine-generated)")
        print(f"  3) mate-in-3 trainer       ({n3} engine-generated)")
        print("  4) streak mode             (3 lives)")
        print("  5) blitz mode              (150 seconds)")
        print("  q) quit")
        try:
            choice = input("\nchoose: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "1":
            mode_classic()
        elif choice == "2":
            mode_depth(2, gen)
        elif choice == "3":
            mode_depth(3, gen)
        elif choice == "4":
            mode_streak(gen)
        elif choice == "5":
            mode_blitz(gen)
        elif choice in ("q", "quit"):
            print("good game!")
            return
        else:
            print("pick 1-5 or q.\n")


if __name__ == "__main__":
    main()
