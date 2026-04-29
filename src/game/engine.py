"""Turn logic and hit/miss handling.

This module currently provides a minimal but working engine that
coordinates two :class:`~src.board.Board` instances.  Front-ends
(CLI, TUI, network) sit on top of it and feed in shots.

If a :class:`~src.game.log.GameLog` is attached, the engine appends a
``"turn"`` event for every shot and a ``"game_end"`` event when the
last ship is sunk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..board import Board
from .log import GameLog


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
    log: Optional[GameLog] = None
    player_names: List[str] = field(
        default_factory=lambda: ["Player 1", "Player 2"]
    )
    _ended_logged: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.boards) != 2:
            raise ValueError("Engine requires exactly two boards")
        if self.current not in (0, 1):
            raise ValueError("current must be 0 or 1")
        if len(self.player_names) != 2:
            raise ValueError("player_names must have length 2")

    @property
    def opponent(self) -> int:
        return 1 - self.current

    def take_turn(self, row: int, col: int) -> TurnResult:
        """Resolve a shot from the current player against the opponent's board."""
        shooter = self.current
        target_board = self.boards[self.opponent]
        outcome = target_board.receive_shot(row, col)
        sunk: Optional[str] = None
        if outcome == "hit":
            for ship in target_board.ships:
                if ship.is_sunk() and (row, col) in ship.cells():
                    sunk = ship.name
                    outcome = "sunk"
                    break
        result = TurnResult(shooter, (row, col), outcome, sunk)
        self.history.append(result)
        if outcome not in ("invalid", "already"):
            self.current = self.opponent
        if self.log is not None:
            self.log.append(
                "turn",
                shooter=shooter,
                shooter_name=self.player_names[shooter],
                target=[row, col],
                target_label=f"{Board._column_label(col)}{row + 1}",
                outcome=outcome,
                sunk_ship=sunk,
            )
            if not self._ended_logged and self.is_over():
                winner = self.winner()
                self.log.append(
                    "game_end",
                    winner=winner,
                    winner_name=(
                        self.player_names[winner] if winner is not None else None
                    ),
                )
                self._ended_logged = True
        return result

    def winner(self) -> Optional[int]:
        """Return the index of the winning player, or None if the game is ongoing."""
        for idx, board in enumerate(self.boards):
            if board.all_sunk():
                return 1 - idx
        return None

    def is_over(self) -> bool:
        return self.winner() is not None
