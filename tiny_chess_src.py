#!/usr/bin/env python3
"""
TinyChess - 4KB chess engine for make.fun tiny-chess-01
Alpha-beta search with transposition table, quiescence, PST, iterative deepening
"""

import json, os, sys, urllib.error, urllib.request as u

ENV = os.environ.get("MAKEFUN_ENV_URL") or sys.exit(1)

# Piece values
VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 10000}

# Piece-square tables (generated programmatically to save space)
def pst(piece):
    """Generate PST for a piece type"""
    if piece == "p":
        return [0]*8 + [50]*8 + [10,10,20,30,30,20,10,10] + [5,5,10,25,25,10,5,5] + [0]*8 + [20,20] + [0]*4 + [5,5,-10,-10] + [0]*8
    if piece == "n":
        return [-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50]
    if piece == "b":
        return [-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20]
    if piece == "r":
        return [0]*8 + [5,10,10,10,10,10,10,5] + [-5,0,0,0,0,0,0,-5]*4 + [-5,0,0,0,5,5,5,5,5,0]
    if piece == "q":
        return [-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,-10,0,5,5,5,5,0,-10,-10,0,5,5,5,5,0,-10,-10,0,0,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20]
    if piece == "k":
        return [-30,-40,-40,-50,-50,-40,-40,-30]*2 + [-20,-30,-30,-40,-40,-30,-30,-20] + [-10,-20,-20,-20,-20,-20,-20,-10] + [20,20,0,0,0,0,20,20] + [20,30,10,0,0,10,30,20]
    return [0]*64

PST = {p: pst(p) for p in "pnbrqk"}

DIRS = {"b": [(-1,-1),(-1,1),(1,-1),(1,1)], "r": [(-1,0),(1,0),(0,-1),(0,1)], "n": [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)], "k": [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]}

def parse(fen):
    """Parse FEN piece placement into {square: piece} dict"""
    board = {}; r = 8; c = 0
    for ch in fen.split()[0]:
        if ch == "/": r -= 1; c = 0
        elif ch.isdigit(): c += int(ch)
        else: board[f"{'abcdefgh'[c]}{r}"] = ch; c += 1
    return board

def sq(s): return (ord(s[0])-97) + 8*(8-int(s[1]))

def make_move(board, move):
    """Make a move on board copy, return captured piece"""
    f, t = move[:2], move[2:4]
    piece = board.pop(f)
    captured = board.get(t)
    board[t] = piece
    if len(move) == 5:
        board[t] = ("q" if piece.islower() else "Q") + move[4]
    return captured

def gen_moves(board, white):
    """Generate all legal moves for side"""
    moves = []
    d = -1 if white else 1
    for f, p in board.items():
        if p.islower() != white: continue
        r, c = divmod(sq(f), 8)
        pt = p.lower()
        if pt == "p":
            fr = r + d
            ft = f"{'abcdefgh'[c]}{8-fr}"
            if 0 <= fr < 8 and ft not in board:
                moves.append(f + ft + ("q" if fr in (0,7) else ""))
                if r == (1 if white else 6) and f"{'abcdefgh'[c]}{8-(fr+d)}" not in board:
                    moves.append(f + f"{'abcdefgh'[c]}{8-(fr+d)}" + "q")
            for df in (-1, 1):
                fc = c + df
                ft = f"{'abcdefgh'[fc]}{8-fr}" if 0 <= fc < 8 else ""
                if ft and board.get(ft, "").islower() != white:
                    moves.append(f + ft + ("q" if fr in (0,7) else ""))
        elif pt == "n":
            for dr, dc in DIRS["n"]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    ft = f"{'abcdefgh'[nc]}{8-nr}"
                    if ft not in board or board[ft].islower() != white:
                        moves.append(f + ft)
        elif pt in "brq":
            for dr, dc in DIRS[pt]:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    ft = f"{'abcdefgh'[nc]}{8-nr}"
                    if ft in board:
                        if board[ft].islower() != white:
                            moves.append(f + ft)
                        break
                    moves.append(f + ft)
                    nr += dr; nc += dc
        elif pt == "k":
            for dr, dc in DIRS["k"]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    ft = f"{'abcdefgh'[nc]}{8-nr}"
                    if ft not in board or board[ft].islower() != white:
                        moves.append(f + ft)
    return moves

def evaluate(board):
    """Static evaluation: material + PST"""
    score = 0
    for f, p in board.items():
        v = VAL[p.lower()] + PST[p.lower()][sq(f)]
        score += v if p.islower() else -v
    return score

TT = {}

def quiesce(board, white, alpha, beta):
    """Quiescence search: captures only"""
    stand = evaluate(board)
    if stand >= beta: return beta
    if stand > alpha: alpha = stand
    for m in [m for m in gen_moves(board, white) if make_move({**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}, m)[0]]:
        nb = {**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}; del nb[m[:2]]
        if len(m) == 5: nb[m[2:4]] = ("q" if board[m[:2]].islower() else "Q") + m[4]
        score = -quiesce(nb, not white, -beta, -alpha)
        if score >= beta: return beta
        if score > alpha: alpha = score
    return alpha

def search(board, white, depth, alpha, beta):
    """Alpha-beta with transposition table"""
    key = "".join(f"{f}{p}" for f, p in sorted(board.items())) + str(white) + str(depth)
    if key in TT and TT[key][1] >= depth:
        return TT[key][0]
    if depth == 0:
        return quiesce(board, white, alpha, beta)
    moves = gen_moves(board, white)
    if not moves:
        return -10000 if any(is_check(board, m) for m in gen_moves(board, not white)) else 0
    # Move ordering: captures first, then promotions, then quiet
    moves.sort(key=lambda m: (make_move({**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}, m)[0] and -VAL[make_move({**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}, m)[0].lower()], -(len(m) > 4 and VAL[m[4]]), VAL[make_move({**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}, m)[0].lower()] if len(m) > 4 else 0, m))
    best = -10000
    for m in moves:
        nb = {**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}; del nb[m[:2]]
        if len(m) == 5: nb[m[2:4]] = ("q" if board[m[:2]].islower() else "Q") + m[4]
        score = -search(nb, not white, depth - 1, -beta, -alpha)
        if score > best: best = score
        if score > alpha: alpha = score
        if alpha >= beta: break
    TT[key] = (best, depth)
    return best

def is_check(board, white):
    """Check if white king is in check"""
    for m in gen_moves(board, not white):
        cap = make_move({**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}, m)
        if cap and cap.lower() == "k":
            return True
    return False

def post(path, body):
    try:
        with u.urlopen(u.Request(ENV + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})) as r:
            return json.load(r)
    except u.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code}")

# Main game loop
while True:
    g = post("/game", {})
    if g["status"] == "done":
        break
    while g["status"] == "your_move":
        board = parse(g["fen"])
        moves = g["legal_moves"]
        white = g["colour"] == "white"
        best_score = -10000
        best_move = moves[0]
        for m in moves:
            nb = {**board, m[:2]: board.get(m[2:4]), m[2:4]: board[m[:2]]}; del nb[m[:2]]
            if len(m) == 5: nb[m[2:4]] = ("q" if board[m[:2]].islower() else "Q") + m[4]
            score = -search(nb, not white, 3, -10000, 10000)
            if score > best_score:
                best_score, best_move = score, m
        g = post("/move", {"game": g["game"], "move": best_move})
        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)