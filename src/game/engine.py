"""Turn logic and hit/miss handling.

This module currently provides a minimal but working engine that
coordinates two :class:`~src.board.Board` instances.  Front-ends
(CLI, TUI, network) sit on top of it and feed in shots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..board import Board


@dataclass
class TurnResult:
    """Outcome of a single shot."""

    shooter: int
    target: Tuple[int, int]
    outcome: str  # "hit" | "miss" | "sunk" | "already" | "invalid"
    sunk_ship: Optional[str] = None


@dataclass
class Engine:
    """Two-player turn engine over a pair of pre-populated boards."""

    boards: List[Board]
    current: int = 0
    history: List[TurnResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.boards) != 2:
            raise ValueError("Engine requires exactly two boards")
        if self.current not in (0, 1):
            raise ValueError("current must be 0 or 1")

    @property
    def opponent(self) -> int:
        return 1 - self.current

    def take_turn(self, row: int, col: int) -> TurnResult:
        """Resolve a shot from the current player against the opponent's board."""
        target_board = self.boards[self.opponent]
        outcome = target_board.receive_shot(row, col)
        sunk: Optional[str] = None
        if outcome == "hit":
            for ship in target_board.ships:
                if ship.is_sunk() and (row, col) in ship.cells():
                    sunk = ship.name
                    outcome = "sunk"
                    break
        result = TurnResult(self.current, (row, col), outcome, sunk)
        self.history.append(result)
        if outcome not in ("invalid", "already"):
            self.current = self.opponent
        return result

    def winner(self) -> Optional[int]:
        """Return the index of the winning player, or None if the game is ongoing."""
        for idx, board in enumerate(self.boards):
            if board.all_sunk():
                return 1 - idx
        return None

    def is_over(self) -> bool:
        return self.winner() is not None
