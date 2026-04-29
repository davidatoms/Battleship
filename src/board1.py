"""Legacy/experimental numpy-based board.

This is kept for reference only.  The authoritative implementation lives
in :mod:`src.board`.  Importing this module without numpy installed will
not fail, but instantiating :class:`NumpyBoard` will.
"""

from __future__ import annotations

try:
    import numpy as np
except ImportError:
    np = None


WATER = 0
SHIP = 1
HIT = 2
MISS = 3


class NumpyBoard:
    """A minimal Battleship grid backed by a numpy array."""

    def __init__(self, size: int = 10):
        if np is None:
            raise ImportError(
                "numpy is required for NumpyBoard; install it via "
                "`pip install numpy`."
            )
        self.size = size
        self.grid = np.zeros((size, size), dtype=np.int8)

    def place(self, row: int, col: int, length: int, vertical: bool = False) -> bool:
        if length <= 0:
            return False
        if vertical:
            if row < 0 or col < 0 or row + length > self.size or col >= self.size:
                return False
            window = self.grid[row : row + length, col]
            if (window != WATER).any():
                return False
            self.grid[row : row + length, col] = SHIP
        else:
            if row < 0 or col < 0 or col + length > self.size or row >= self.size:
                return False
            window = self.grid[row, col : col + length]
            if (window != WATER).any():
                return False
            self.grid[row, col : col + length] = SHIP
        return True

    def shoot(self, row: int, col: int) -> str:
        if not (0 <= row < self.size and 0 <= col < self.size):
            return "invalid"
        cell = int(self.grid[row, col])
        if cell == SHIP:
            self.grid[row, col] = HIT
            return "hit"
        if cell == WATER:
            self.grid[row, col] = MISS
        return "miss"

    def __repr__(self) -> str:
        return f"NumpyBoard(size={self.size})\n{self.grid!r}"
