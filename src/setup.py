"""Interactive fleet-placement helper.

A :class:`Setup` instance walks the player through placing each ship in
a fleet.  It exposes a small, framework-agnostic API so the same logic
can drive a CLI prompt, a curses TUI, or any GUI:

* :meth:`Setup.move_cursor` -- step the placement cursor one cell
  ``"up"``, ``"down"``, ``"left"``, or ``"right"``.
* :meth:`Setup.rotate_current` -- rotate the active ship using the
  WASD keys (``"w"`` = up/0 degrees, ``"d"`` = right/90, ``"s"`` =
  down/180, ``"a"`` = left/270).
* :meth:`Setup.commit_ship` -- attempt to place the active ship at the
  current cursor and orientation.  Returns ``False`` if it would be
  out of bounds or overlap an existing ship.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .board import Board
from .ship import EAST, NORTH, SOUTH, WEST, Ship, standard_fleet


_DIRECTION_DELTAS = {
    "up":    (-1,  0),
    "down":  ( 1,  0),
    "left":  ( 0, -1),
    "right": ( 0,  1),
}


_ROTATE_KEYS = {
    "w": NORTH,
    "d": EAST,
    "s": SOUTH,
    "a": WEST,
}


class Setup:
    """Drive interactive fleet placement on a :class:`Board`."""

    def __init__(
        self,
        board: Optional[Board] = None,
        fleet: Optional[Sequence[Ship]] = None,
    ) -> None:
        self.board = board if board is not None else Board()
        self.fleet: List[Ship] = list(fleet) if fleet is not None else standard_fleet()
        self.cursor: Tuple[int, int] = (0, 0)
        self._index = 0
        self._sync_anchor()

    @property
    def current_ship(self) -> Optional[Ship]:
        if self._index >= len(self.fleet):
            return None
        return self.fleet[self._index]

    @property
    def remaining(self) -> List[Ship]:
        return self.fleet[self._index:]

    @property
    def placed(self) -> List[Ship]:
        return self.fleet[: self._index]

    @property
    def done(self) -> bool:
        return self.current_ship is None

    def move_cursor(self, direction: str) -> Tuple[int, int]:
        """Move the cursor one cell, clamped to the board."""
        try:
            dr, dc = _DIRECTION_DELTAS[direction]
        except KeyError as exc:
            raise ValueError(
                f"unknown direction {direction!r}; expected one of "
                f"{sorted(_DIRECTION_DELTAS)}"
            ) from exc
        r, c = self.cursor
        new_r = max(0, min(self.board.size - 1, r + dr))
        new_c = max(0, min(self.board.size - 1, c + dc))
        self.cursor = (new_r, new_c)
        self._sync_anchor()
        return self.cursor

    def rotate_current(self, key: str) -> None:
        """Rotate the active ship using a WASD key."""
        try:
            new_orientation = _ROTATE_KEYS[key]
        except KeyError as exc:
            raise ValueError(
                f"unknown rotate key {key!r}; expected one of "
                f"{sorted(_ROTATE_KEYS)}"
            ) from exc
        ship = self.current_ship
        if ship is None:
            return
        ship.orientation = new_orientation

    def can_commit(self) -> bool:
        ship = self.current_ship
        if ship is None:
            return False
        return self.board.can_place(ship)

    def commit_ship(self) -> bool:
        """Place the active ship; advance to the next ship on success."""
        ship = self.current_ship
        if ship is None:
            return False
        if not self.board.place_ship(ship):
            return False
        self._index += 1
        self._sync_anchor()
        return True

    def preview_cells(self) -> List[Tuple[int, int]]:
        """Cells the active ship would occupy if committed right now."""
        ship = self.current_ship
        if ship is None:
            return []
        return ship.cells()

    def display(self) -> str:
        return self.board.display(cursor=self.cursor, preview=self.preview_cells())

    def render(self) -> str:
        return self.board.render(cursor=self.cursor, preview=self.preview_cells())

    def _sync_anchor(self) -> None:
        ship = self.current_ship
        if ship is None:
            return
        ship.anchor = self.cursor
