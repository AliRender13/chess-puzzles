"""
generate.py — build verified mate-in-2 / mate-in-3 puzzles.

Samples random endgame positions, then *proves* each puzzle with the
engine in chess.py: a puzzle is only kept if the search confirms a forced
mate in exactly N (and no faster mate exists). Results go to generated.json.

Run:
    python3 generate.py [seed]
"""
import json
import os
import random
import sys
import time

from chess import (Position, parse_fen, to_fen, legal_moves, make, unmake,
                   in_check, is_stalemate, is_checkmate, forced_mate,
                   find_key_moves, gives_check, gives_mate, to_san,
                   square_name, PIECE_NAMES)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "generated.json")

LABELS = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}


def sample_position(rng, white_extra, black_extra, center_bias=False):
    """Random plausible endgame position, White to move, nobody in check."""
    def rsq():
        return (rng.randrange(8), rng.randrange(8))

    def far(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1])) > 1

    for _ in range(300):
        if center_bias and rng.random() < 0.65:
            bk = (rng.randrange(2, 6), rng.randrange(2, 6))
        else:
            bk = rsq()
        wk = rsq()
        if not far(bk, wk):
            continue
        board = [["."] * 8 for _ in range(8)]
        board[bk[0]][bk[1]] = "k"
        board[wk[0]][wk[1]] = "K"
        ok = True
        for p in white_extra:
            for _ in range(300):
                s = rsq()
                if board[s[0]][s[1]] == ".":
                    break
            else:
                ok = False
                break
            board[s[0]][s[1]] = p
        for p in black_extra:
            for _ in range(300):
                s = rsq()
                if board[s[0]][s[1]] != ".":
                    continue
                if p == "p" and s[0] in (0, 7):
                    continue  # no pawns stuck on the last rank
                break
            else:
                ok = False
                break
            board[s[0]][s[1]] = p.lower()
        if not ok:
            continue
        pos = Position(board, "w")
        if in_check(pos):
            continue
        pos.turn = "b"
        if in_check(pos):
            continue
        pos.turn = "w"
        if is_stalemate(pos):
            continue
        if len(legal_moves(pos)) < 6:
            continue
        return pos
    return None


def order_key_candidates(pos):
    """Heuristic order for mate-in-3 key search: checks, captures, queen."""
    moves = legal_moves(pos)

    def score(m):
        r0, c0, r1, c1, promo = m
        s = 0
        if gives_check(pos, m):
            s -= 100
        if pos.board[r1][c1] != ".":
            s -= 10
        if pos.board[r0][c0].upper() == "Q":
            s -= 5
        return s

    return sorted(moves, key=score)


def find_m3_keys(pos, limit=3):
    """Key moves that force mate in exactly 3 (mate-in-2 already excluded)."""
    keys = []
    for m in order_key_candidates(pos):
        if gives_mate(pos, m):
            continue
        undo = make(pos, m)
        if is_stalemate(pos):
            unmake(pos, m, undo)
            continue
        ok = True
        for r in legal_moves(pos):
            undo_r = make(pos, r)
            sub = forced_mate(pos, 2)
            unmake(pos, r, undo_r)
            if not sub:
                ok = False
                break
        unmake(pos, m, undo)
        if ok:
            keys.append(m)
            if len(keys) >= limit:
                break
    return keys


def classify(pos):
    """(n, keys) with a proven forced mate in exactly n in {2, 3}, else None."""
    if forced_mate(pos, 1):
        return None
    if forced_mate(pos, 2):
        keys = find_key_moves(pos, 2, limit=4)
        return (2, keys) if keys else None
    keys = find_m3_keys(pos, limit=3)
    return (3, keys) if keys else None


def rate(pos, keys, depth):
    """Difficulty stars from branching, defenses and key-move subtlety."""
    n_moves = len(legal_moves(pos))
    undo = make(pos, keys[0])
    n_def = len(legal_moves(pos))
    unmake(pos, keys[0], undo)
    r0, c0, r1, c1, _ = keys[0]
    quiet = not gives_check(pos, keys[0]) and pos.board[r1][c1] == "."
    stars = depth
    if n_moves >= 28:
        stars += 1
    if n_def >= 8:
        stars += 1
    if quiet:
        stars += 1
    stars = max(1, min(5, stars))
    return stars, LABELS[stars], {
        "legal_moves": n_moves, "defenses": n_def, "quiet_key": quiet}


def play(pos, m):
    """SAN + squares for a move, then apply it. Returns (info, undo)."""
    info = {"san": to_san(pos, m), "from": [m[0], m[1]], "to": [m[2], m[3]],
            "piece": PIECE_NAMES[pos.board[m[0]][m[1]].upper()]}
    return info, make(pos, m)


def first_mate_move(pos):
    for m in legal_moves(pos):
        if gives_mate(pos, m):
            return m
    return None


def build_lines(pos, keys, depth):
    """Sample forced lines for display: list of defenses, each a move list."""
    key = keys[0]
    key_info, undo_k = play(pos, key)
    replies = legal_moves(pos)
    lines, demo = [], None
    max_def = 4 if depth == 2 else 2
    for r in replies[:max_def]:
        r_info, undo_r = play(pos, r)
        if depth == 2:
            mate = first_mate_move(pos)
            mate_info, undo_m = play(pos, mate)
            line = [key_info, r_info, mate_info]
            unmake(pos, mate, undo_m)
            lines.append(line)
            if demo is None:
                demo = line
        else:
            m2 = find_key_moves(pos, 2, limit=1)
            if not m2:
                unmake(pos, r, undo_r)
                continue
            m2 = m2[0]
            m2_info, undo_m2 = play(pos, m2)
            sub_replies = legal_moves(pos)[:2]
            for r2 in sub_replies:
                r2_info, undo_r2 = play(pos, r2)
                mate = first_mate_move(pos)
                if mate is None:
                    unmake(pos, r2, undo_r2)
                    continue
                mate_info, undo_m = play(pos, mate)
                line = [key_info, r_info, m2_info, r2_info, mate_info]
                unmake(pos, mate, undo_m)
                lines.append(line)
                if demo is None:
                    demo = line
                unmake(pos, r2, undo_r2)
                if len(lines) >= 4:
                    break
            unmake(pos, m2, undo_m2)
        unmake(pos, r, undo_r)
        if len(lines) >= 4:
            break
    unmake(pos, key, undo_k)
    return lines, demo


def key_sans(pos, keys):
    return [to_san(pos, m).replace("+", "").replace("#", "") for m in keys]


def build_puzzle(pos, keys, depth, stars, label, idx):
    fen = to_fen(pos)
    sans = key_sans(pos, keys)
    lines, demo = build_lines(pos, keys, depth)
    key = keys[0]
    return {
        "name": f"Mate in {depth} · {label} #{idx + 1}",
        "fen": fen,
        "depth": depth,
        "stars": stars,
        "label": label,
        "keys": sans,                      # all accepted key moves (SAN, no +/#)
        "hint_piece": PIECE_NAMES[pos.board[key[0]][key[1]].upper()],
        "hint_square": square_name(key[2], key[3]),
        "lines": lines,                    # sample forced continuations
        "demo": demo,                      # one full line for the video
    }


def verify_puzzle(p):
    """Independent re-proof: parse the FEN, confirm exact mate distance and keys."""
    pos = parse_fen(p["fen"])
    n = p["depth"]
    if forced_mate(pos, 1):
        return False, "mate in 1 exists"
    if n == 2:
        if not forced_mate(pos, 2):
            return False, "no mate in 2"
    else:
        if forced_mate(pos, 2):
            return False, "mate in 2 exists, not 3"
        if not find_m3_keys(pos, limit=1):
            return False, "no mate-in-3 key"
    legal = legal_moves(pos)
    sans = {to_san(pos, m).replace("+", "").replace("#", ""): m for m in legal}
    for k in p["keys"]:
        if k not in sans:
            return False, f"stored key {k} not legal"
    return True, "ok"


def generate_wanted(rng, depth, count, specs, center_bias=False):
    got, attempts = [], 0
    t0 = time.time()
    while len(got) < count and attempts < 6000:
        attempts += 1
        spec = rng.choice(specs)
        pos = sample_position(rng, spec[0], spec[1], center_bias)
        if pos is None:
            continue
        res = classify(pos)
        if res is None or res[0] != depth:
            continue
        n, keys = res
        stars, label, _ = rate(pos, keys, depth)
        p = build_puzzle(pos, keys, depth, stars, label, len(got))
        ok, msg = verify_puzzle(p)
        if not ok:
            print(f"  !! verification failed ({msg}), discarded", flush=True)
            continue
        got.append(p)
        print(f"  [{depth}] {len(got)}/{count}: {p['name']} "
              f"key={p['keys'][0]} ({time.time()-t0:.0f}s, {attempts} tried)",
              flush=True)
    return got


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 20260928
    rng = random.Random(seed)
    print(f"seed {seed}", flush=True)

    print("generating mate-in-2 puzzles...", flush=True)
    m2 = generate_wanted(rng, 2, 6,
                         [(["Q"], []), (["R", "R"], []),
                          (["Q"], ["p"]), (["R"], ["p"])])
    print("generating mate-in-3 puzzles...", flush=True)
    m3 = generate_wanted(rng, 3, 4,
                         [(["Q"], []), (["Q"], ["p"]),
                          (["R", "R"], []), (["Q"], ["p", "p"])],
                         center_bias=True)

    data = {"mate_in_2": m2, "mate_in_3": m3}
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {OUT}: {len(m2)} mate-in-2, {len(m3)} mate-in-3", flush=True)


if __name__ == "__main__":
    main()
