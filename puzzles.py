"""
chess-puzzles
A mate-in-one chess puzzle trainer in pure Python (no dependencies).

Shows famous checkmate-in-one positions as ASCII boards and quizzes you:
find the winning move. Solutions are checked, hints are available.

Run:
    python3 puzzles.py
"""

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


def parse_fen(fen):
    """Parse the piece-placement field of a FEN string into an 8x8 board."""
    board = []
    for rank in fen.split(" ")[0].split("/"):
        row = []
        for ch in rank:
            if ch.isdigit():
                row += ["."] * int(ch)
            else:
                row.append(ch)
        board.append(row)
    return board


def show(board):
    print("  +-----------------+")
    for i, row in enumerate(board):
        print(f"{8 - i} | {' '.join(row)} |")
    print("  +-----------------+")
    print("    a b c d e f g h")


def normalise(move):
    return move.strip().upper().replace("#", "").replace("+", "")


def main():
    print("♞  Mate-in-one trainer — White to move and checkmate.\n"
          "   Type your move (e.g. Re8), 'hint' for a tip, 'quit' to stop.\n")
    score = 0
    for n, p in enumerate(PUZZLES, 1):
        print(f"--- Puzzle {n}/{len(PUZZLES)}: {p['name']} ---")
        show(parse_fen(p["fen"]))
        while True:
            ans = input("your move: ")
            if normalise(ans) == "QUIT":
                print(f"\nfinal score: {score}/{len(PUZZLES)}")
                return
            if normalise(ans) == "HINT":
                print(f"hint: {p['tip']}")
                continue
            if normalise(ans) in p["solution"]:
                print("correct! checkmate.\n")
                score += 1
                break
            print("not quite — try again (or type 'hint').")
    print(f"done! final score: {score}/{len(PUZZLES)}")


if __name__ == "__main__":
    main()
