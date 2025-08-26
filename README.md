# Battleship (Python)

A modular, extensible implementation of the classic *Battleship* board-game written in Python.  The codebase is intentionally kept framework-agnostic so you can wire it to any front-end: command-line, *curses*, Pygame, or even the web.

---

## Repository structure

```
Battleship/
├── src/
│   ├── board.py          # Board model & rendering helpers
│   ├── board1.py         # (legacy/experimental) numpy-based board
│   ├── ship.py           # Ship dataclass + concrete fleet types
│   ├── setup.py          # Interactive fleet-placement helper
│   └── game/
│       ├── engine.py     # (stub) turn logic & hit/miss handling
│       └── modes.py      # (stub) single- & multi-player modes
└── tests/                # Place unit-tests here
```

## Features so far

* 10 × 10 board with pretty printing (row/column headers).
* `Ship` dataclass supplies:
  * Carrier (length 5)
  * Battleship (4)
  * Cruiser (3)
  * Submarine (3)
  * Destroyer (2)
* `Setup` helper allows each player to place ships interactively:
  * Move cursor – `up`, `down`, `left`, `right`
  * Rotate – `w` (0°), `d` (90°), `s` (180°), `a` (270°)
  * Non-overlapping & in-bounds validation
* Straight-line and diagonal orientations supported in the model (diagonals not yet wired to keys).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # currently only needs numpy (optional)
python
```

```python
from src.setup import Setup

setup = Setup()

# place the first ship manually
setup.move_cursor("right")
setup.rotate_current("d")   # 90°
setup.commit_ship()

setup.board.display()
```

## Roadmap

1. Flesh out `game/engine.py` to handle turns, hit/miss logic, sinking, win condition.
2. Add a curses-based TUI for full interactive play.
3. Optional AI opponent – integrate search/heuristics for single player.
4. Network play via sockets or WebSocket for online multiplayer.

Contributions welcome!  Feel free to open issues or submit pull requests.

# Battleship
