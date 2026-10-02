"""
chess.py — a complete little chess engine in pure Python (standard library only).

Board, full legal move generation (castling, en passant, promotion),
check / checkmate / stalemate detection, SAN notation, FEN parsing and
generation, and a proof-search that *proves* forced mate in N moves.

Board representation: board[r][c], r=0 is rank 8, r=7 is rank 1.
'.' = empty, uppercase = White, lowercase = Black.
"""

KNIGHT_D = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)]
KING_D = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
          (0, 1), (1, -1), (1, 0), (1, 1)]
ROOK_D = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_D = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

PIECE_NAMES = {"K": "King", "Q": "Queen", "R": "Rook",
               "B": "Bishop", "N": "Knight", "P": "Pawn"}


def opp(color):
    return "b" if color == "w" else "w"


def on_board(r, c):
    return 0 <= r < 8 and 0 <= c < 8


class Position:
    """Mutable chess position with make/unmake move support."""
    __slots__ = ("board", "turn", "castling", "ep")

    def __init__(self, board, turn="w", castling=frozenset(), ep=None):
        self.board = board            # 8x8 list of lists
        self.turn = turn              # 'w' or 'b'
        self.castling = set(castling)  # subset of {'K','Q','k','q'}
        self.ep = ep                  # (r, c) en-passant target square or None

    def copy(self):
        return Position([row[:] for row in self.board],
                        self.turn, set(self.castling), self.ep)


# --------------------------------------------------------------------------
# FEN
# --------------------------------------------------------------------------

def parse_fen(fen):
    """Parse a FEN string into a Position (piece placement, turn, castling, ep)."""
    parts = fen.split(" ")
    board = []
    for rank in parts[0].split("/"):
        row = []
        for ch in rank:
            if ch.isdigit():
                row += ["."] * int(ch)
            else:
                row.append(ch)
        board.append(row)
    turn = parts[1] if len(parts) > 1 else "w"
    castling = set(parts[2]) if len(parts) > 2 and parts[2] != "-" else set()
    ep = None
    if len(parts) > 3 and parts[3] != "-":
        ep = (8 - int(parts[3][1]), ord(parts[3][0]) - ord("a"))
    return Position(board, turn, castling, ep)


def to_fen(pos):
    rows = []
    for row in pos.board:
        out, n = "", 0
        for sq in row:
            if sq == ".":
                n += 1
            else:
                if n:
                    out += str(n)
                    n = 0
                out += sq
        if n:
            out += str(n)
        rows.append(out)
    ep = "-" if pos.ep is None else chr(ord("a") + pos.ep[1]) + str(8 - pos.ep[0])
    castling = "".join(c for c in "KQkq" if c in pos.castling) or "-"
    return f"{'/'.join(rows)} {pos.turn} {castling} {ep} 0 1"


def square_name(r, c):
    return chr(ord("a") + c) + str(8 - r)


# --------------------------------------------------------------------------
# Attack detection
# --------------------------------------------------------------------------

def is_attacked(board, r, c, by):
    """Is square (r, c) attacked by color `by` ('w' or 'b')?"""
    # pawns
    if by == "w":
        for dc in (-1, 1):
            rr, cc = r + 1, c + dc
            if on_board(rr, cc) and board[rr][cc] == "P":
                return True
    else:
        for dc in (-1, 1):
            rr, cc = r - 1, c + dc
            if on_board(rr, cc) and board[rr][cc] == "p":
                return True
    # knights
    n = "N" if by == "w" else "n"
    for dr, dc in KNIGHT_D:
        rr, cc = r + dr, c + dc
        if on_board(rr, cc) and board[rr][cc] == n:
            return True
    # king
    k = "K" if by == "w" else "k"
    for dr, dc in KING_D:
        rr, cc = r + dr, c + dc
        if on_board(rr, cc) and board[rr][cc] == k:
            return True
    # sliders
    rq = ("R", "Q") if by == "w" else ("r", "q")
    for dr, dc in ROOK_D:
        rr, cc = r + dr, c + dc
        while on_board(rr, cc):
            p = board[rr][cc]
            if p != ".":
                if p in rq:
                    return True
                break
            rr, cc = rr + dr, cc + dc
    bq = ("B", "Q") if by == "w" else ("b", "q")
    for dr, dc in BISHOP_D:
        rr, cc = r + dr, c + dc
        while on_board(rr, cc):
            p = board[rr][cc]
            if p != ".":
                if p in bq:
                    return True
                break
            rr, cc = rr + dr, cc + dc
    return False


def find_king(board, color):
    k = "K" if color == "w" else "k"
    for r in range(8):
        for c in range(8):
            if board[r][c] == k:
                return (r, c)
    return None


# --------------------------------------------------------------------------
# Move generation (pseudo-legal)
# --------------------------------------------------------------------------

def gen_pseudo(pos):
    """All pseudo-legal moves for the side to move.
    Move = (r0, c0, r1, c1, promo) with promo in {None,'Q','R','B','N'}."""
    board, turn = pos.board, pos.turn
    moves = []
    white = turn == "w"

    def own(p):
        return p != "." and (p.isupper() == white)

    def free_or_enemy(r, c):
        return on_board(r, c) and not own(board[r][c])

    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if not own(p):
                continue
            pt = p.upper()
            if pt == "P":
                direction = -1 if white else 1
                start = 6 if white else 1
                last_rank = 0 if white else 7
                # pushes
                if on_board(r + direction, c) and board[r + direction][c] == ".":
                    if r + direction == last_rank:
                        for pr in ("Q", "R", "B", "N"):
                            moves.append((r, c, r + direction, c, pr))
                    else:
                        moves.append((r, c, r + direction, c, None))
                        if r == start and board[r + 2 * direction][c] == ".":
                            moves.append((r, c, r + 2 * direction, c, None))
                # captures (incl. en passant)
                for dc in (-1, 1):
                    rr, cc = r + direction, c + dc
                    if not on_board(rr, cc):
                        continue
                    is_ep = pos.ep == (rr, cc)
                    target = board[rr][cc]
                    if (target != "." and not own(target)) or is_ep:
                        if rr == last_rank:
                            for pr in ("Q", "R", "B", "N"):
                                moves.append((r, c, rr, cc, pr))
                        else:
                            moves.append((r, c, rr, cc, None))
            elif pt == "N":
                for dr, dc in KNIGHT_D:
                    rr, cc = r + dr, c + dc
                    if free_or_enemy(rr, cc):
                        moves.append((r, c, rr, cc, None))
            elif pt in ("B", "R", "Q"):
                dirs = {"B": BISHOP_D, "R": ROOK_D, "Q": BISHOP_D + ROOK_D}[pt]
                for dr, dc in dirs:
                    rr, cc = r + dr, c + dc
                    while on_board(rr, cc):
                        if own(board[rr][cc]):
                            break
                        moves.append((r, c, rr, cc, None))
                        if board[rr][cc] != ".":
                            break
                        rr, cc = rr + dr, cc + dc
            elif pt == "K":
                for dr, dc in KING_D:
                    rr, cc = r + dr, c + dc
                    if free_or_enemy(rr, cc):
                        moves.append((r, c, rr, cc, None))
                # castling
                home = 7 if white else 0
                enemy = opp(turn)
                if r == home and c == 4 and not is_attacked(board, r, c, enemy):
                    ks = "K" if white else "k"
                    qs = "Q" if white else "q"
                    if ks in pos.castling and board[home][5] == "." \
                            and board[home][6] == "." \
                            and not is_attacked(board, home, 5, enemy) \
                            and not is_attacked(board, home, 6, enemy):
                        moves.append((r, c, home, 6, None))
                    if qs in pos.castling and board[home][3] == "." \
                            and board[home][2] == "." and board[home][1] == "." \
                            and not is_attacked(board, home, 3, enemy) \
                            and not is_attacked(board, home, 2, enemy):
                        moves.append((r, c, home, 2, None))
    return moves


# --------------------------------------------------------------------------
# Make / unmake
# --------------------------------------------------------------------------

def make(pos, move):
    """Apply a move; returns undo info for unmake()."""
    r0, c0, r1, c1, promo = move
    board = pos.board
    piece = board[r0][c0]
    white = piece.isupper()
    captured = board[r1][c1]
    ep_capture = piece.upper() == "P" and pos.ep == (r1, c1) and captured == "."
    if ep_capture:
        captured = board[r0][c1]
        board[r0][c1] = "."
    undo = [captured, set(pos.castling), pos.ep, ep_capture, None]
    board[r0][c0] = "."
    board[r1][c1] = piece if promo is None else (promo if white else promo.lower())
    # castling rook hop
    if piece.upper() == "K" and abs(c1 - c0) == 2:
        if c1 == 6:
            board[r0][5] = board[r0][7]
            board[r0][7] = "."
            undo[4] = (r0, 7, r0, 5)
        else:
            board[r0][3] = board[r0][0]
            board[r0][0] = "."
            undo[4] = (r0, 0, r0, 3)
    # castling rights
    if piece.upper() == "K":
        pos.castling.discard("K" if white else "k")
        pos.castling.discard("Q" if white else "q")
    for sq, right in [((7, 0), "Q"), ((7, 7), "K"),
                      ((0, 0), "q"), ((0, 7), "k")]:
        if (r0, c0) == sq or (r1, c1) == sq:
            pos.castling.discard(right)
    # ep square
    pos.ep = None
    if piece.upper() == "P" and abs(r1 - r0) == 2:
        pos.ep = ((r0 + r1) // 2, c0)
    pos.turn = opp(pos.turn)
    return undo


def unmake(pos, move, undo):
    """Undo a move previously applied with make()."""
    r0, c0, r1, c1, promo = move
    captured, old_castling, old_ep, ep_capture, rook = undo
    board = pos.board
    pos.turn = opp(pos.turn)
    pos.castling = old_castling
    pos.ep = old_ep
    if rook is not None:
        rr0, cc0, rr1, cc1 = rook
        board[rr0][cc0] = board[rr1][cc1]
        board[rr1][cc1] = "."
    piece = board[r1][c1]
    mover = ("P" if piece.isupper() else "p") if promo is not None else piece
    board[r0][c0] = mover
    board[r1][c1] = "."
    if captured != ".":
        if ep_capture:
            board[r0][c1] = captured
        else:
            board[r1][c1] = captured


def legal_moves(pos):
    """All legal moves for the side to move."""
    out = []
    for m in gen_pseudo(pos):
        undo = make(pos, m)
        ksq = find_king(pos.board, opp(pos.turn))
        if ksq is not None and not is_attacked(pos.board, ksq[0], ksq[1], pos.turn):
            out.append(m)
        unmake(pos, m, undo)
    return out


def in_check(pos):
    ksq = find_king(pos.board, pos.turn)
    return ksq is not None and is_attacked(pos.board, ksq[0], ksq[1], opp(pos.turn))


def is_checkmate(pos):
    return in_check(pos) and not legal_moves(pos)


def is_stalemate(pos):
    return not in_check(pos) and not legal_moves(pos)


def gives_check(pos, move):
    undo = make(pos, move)
    chk = in_check(pos)
    unmake(pos, move, undo)
    return chk


def gives_mate(pos, move):
    undo = make(pos, move)
    mate = is_checkmate(pos)
    unmake(pos, move, undo)
    return mate


# --------------------------------------------------------------------------
# SAN notation
# --------------------------------------------------------------------------

def to_san(pos, move):
    """SAN for a move in the current position (call before making it)."""
    r0, c0, r1, c1, promo = move
    piece = pos.board[r0][c0]
    pt = piece.upper()
    legal = legal_moves(pos)
    dest = square_name(r1, c1)
    san = ""
    if pt == "K" and abs(c1 - c0) == 2:  # castling
        san = "O-O" if c1 == 6 else "O-O-O"
    elif pt == "P":
        if c0 != c1 or pos.board[r1][c1] != "." or pos.ep == (r1, c1):
            san += chr(ord("a") + c0) + "x"
        san += dest
        if promo:
            san += "=" + promo
    else:
        san += pt
        # disambiguation (m layout is (r0,c0,r1,c1,promo))
        others = [m for m in legal
                  if m != move and pos.board[m[0]][m[1]].upper() == pt
                  and m[2] == r1 and m[3] == c1]
        if others:
            same_file = any(m[1] == c0 for m in others)
            same_rank = any(m[0] == r0 for m in others)
            if not same_file:
                san += chr(ord("a") + c0)
            elif not same_rank:
                san += str(8 - r0)
            else:
                san += square_name(r0, c0)
        if pos.board[r1][c1] != "." or (pt == "P" and pos.ep == (r1, c1)):
            san += "x"
        san += dest
    undo = make(pos, move)
    if is_checkmate(pos):
        san += "#"
    elif in_check(pos):
        san += "+"
    unmake(pos, move, undo)
    return san


# --------------------------------------------------------------------------
# Mate proof search
# --------------------------------------------------------------------------

def order_moves(pos, moves):
    """Checks and captures first — massively prunes mate search."""
    scored = []
    for m in moves:
        r0, c0, r1, c1, promo = m
        cap = pos.board[r1][c1] != "." or (
            pos.board[r0][c0].upper() == "P" and pos.ep == (r1, c1))
        scored.append((0 if cap else 1, m))
    scored.sort(key=lambda x: x[0])
    checks, rest = [], []
    for _, m in scored:
        (checks if gives_check(pos, m) else rest).append(m)
    return checks + rest


def forced_mate(pos, depth):
    """True if the side to move forces checkmate within `depth` of its
    own moves (depth=1 means mate on this move). Proven by search."""
    if depth <= 0:
        return False
    moves = order_moves(pos, legal_moves(pos))
    for m in moves:
        if gives_mate(pos, m):
            return True
    if depth == 1:
        return False
    for m in moves:
        undo = make(pos, m)
        if is_stalemate(pos):
            unmake(pos, m, undo)
            continue
        ok = True
        for r in legal_moves(pos):
            undo_r = make(pos, r)
            sub = forced_mate(pos, depth - 1)
            unmake(pos, r, undo_r)
            if not sub:
                ok = False
                break
        unmake(pos, m, undo)
        if ok:
            return True
    return False


def find_key_moves(pos, depth, limit=4):
    """All first moves that force mate in exactly `depth` (side to move).

    A key move either mates immediately (depth==1) or leaves the opponent
    with only replies that allow forced mate in depth-1."""
    keys = []
    for m in order_moves(pos, legal_moves(pos)):
        if gives_mate(pos, m):
            if depth == 1:
                keys.append(m)
            continue
        if depth == 1:
            continue
        undo = make(pos, m)
        if is_stalemate(pos):
            unmake(pos, m, undo)
            continue
        ok = True
        for r in legal_moves(pos):
            undo_r = make(pos, r)
            sub = forced_mate(pos, depth - 1)
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


def find_mate_after(pos, depth):
    """First move (in search order) that forces mate in `depth`. None if none."""
    keys = find_key_moves(pos, depth, limit=1)
    return keys[0] if keys else None


def perft(pos, depth):
    """Node counter — validates move generation against known values."""
    if depth == 0:
        return 1
    n = 0
    for m in legal_moves(pos):
        undo = make(pos, m)
        n += perft(pos, depth - 1)
        unmake(pos, m, undo)
    return n
