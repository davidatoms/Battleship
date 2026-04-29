"""Board model and rendering helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .ship import Ship


WATER = "."
SHIP_CELL = "S"
HIT = "X"
MISS = "o"
PREVIEW = "+"
CURSOR = "@"


class Board:
    """Square Battleship grid that owns ships and renders itself in ASCII."""

    DEFAULT_SIZE = 10

    def __init__(self, size: int = DEFAULT_SIZE) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        self.size = size
        self._grid: List[List[str]] = [[WATER] * size for _ in range(size)]
        self.ships: List[Ship] = []

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def cell(self, row: int, col: int) -> str:
        return self._grid[row][col]

    def is_occupied(self, row: int, col: int) -> bool:
        return self._grid[row][col] == SHIP_CELL

    def can_place(self, ship: Ship) -> bool:
        cells = ship.cells()
        if not cells:
            return False
        for r, c in cells:
            if not self.in_bounds(r, c):
                return False
            if self._grid[r][c] != WATER:
                return False
        return True

    def place_ship(self, ship: Ship) -> bool:
        """Place ``ship`` on the grid; return True on success, False otherwise."""
        if not self.can_place(ship):
            return False
        for r, c in ship.cells():
            self._grid[r][c] = SHIP_CELL
        self.ships.append(ship)
        return True

    def receive_shot(self, row: int, col: int) -> str:
        """Resolve a shot at ``(row, col)``.

        Returns one of ``"hit"``, ``"miss"``, ``"already"``, or ``"invalid"``.
        """
        if not self.in_bounds(row, col):
            return "invalid"
        current = self._grid[row][col]
        if current in (HIT, MISS):
            return "already"
        for ship in self.ships:
            if (row, col) in ship.cells():
                ship.hit_at(row, col)
                self._grid[row][col] = HIT
                return "hit"
        self._grid[row][col] = MISS
        return "miss"

    def all_sunk(self) -> bool:
        return bool(self.ships) and all(s.is_sunk() for s in self.ships)

    def render(
        self,
        *,
        hidden: bool = False,
        cursor: Optional[Tuple[int, int]] = None,
        preview: Optional[Iterable[Tuple[int, int]]] = None,
    ) -> str:
        """Build the printable representation of the board without printing it."""
        headers = [self._column_label(c) for c in range(self.size)]
        row_label_width = len(str(self.size))
        lines: List[str] = []
        lines.append(" " * (row_label_width + 1) + " ".join(headers))
        preview_set = set(preview) if preview else set()
        for r in range(self.size):
            row_label = f"{r + 1:>{row_label_width}}"
            cells: List[str] = []
            for c in range(self.size):
                ch = self._grid[r][c]
                if hidden and ch == SHIP_CELL:
                    ch = WATER
                if (r, c) in preview_set and ch in (WATER, SHIP_CELL):
                    ch = PREVIEW
                if cursor == (r, c):
                    ch = CURSOR
                cells.append(ch)
            lines.append(f"{row_label} " + " ".join(cells))
        return "\n".join(lines)

    def display(
        self,
        *,
        hidden: bool = False,
        cursor: Optional[Tuple[int, int]] = None,
        preview: Optional[Iterable[Tuple[int, int]]] = None,
    ) -> str:
        """Print the board and return the rendered string."""
        rendered = self.render(hidden=hidden, cursor=cursor, preview=preview)
        print(rendered)
        return rendered

    @staticmethod
    def _column_label(index: int) -> str:
        # Excel-style: A..Z, AA..AZ, BA.. for boards larger than 26 columns.
        label = ""
        n = index
        while True:
            label = chr(ord("A") + n % 26) + label
            n = n // 26 - 1
            if n < 0:
                return label
