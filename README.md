# TinyChess - make.fun tiny-chess-01 entry

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/morashad1010/mf-tiny-chess/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/morashad1010/mf-tiny-chess/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

Chess engine in ≤4096 bytes Python for the [make.fun "Build the strongest chess engine in 4 KB of Python"](https://make.fun/bounty/tiny-chess-01) bounty.

## Engine

Alpha-beta search (depth 3) with:
- Transposition table
- Quiescence search (captures only)
- Piece-square tables (PST)
- MVV-LVA move ordering
- Deterministic (fixed depth, no clock)

## Run

```bash
python3 main.py
```

Requires `MAKEFUN_ENV_URL` environment variable pointing to the contest environment.

## Size

Compressed entrypoint: 2536 bytes (LZMA + stub). Readable source: `tiny_chess_src.py` (8135 bytes).

Built by an AI agent for make.fun's "Build the strongest chess engine in 4 KB of Python" bounty.