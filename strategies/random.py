"""Uniform random shooting among unresolved cells."""

from __future__ import annotations

import random
from typing import Optional

from src.game.engine import Engine, TurnResult


class RandomShooting:
    def __init__(self, size: int = 10, seed: Optional[int] = None):
        self.size = size
        self.rng = random.Random(seed)

    def take_turn(self, engine: Engine) -> TurnResult:
        target_board = engine.boards[1 - engine.current]
        choices = [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if target_board.cell(r, c) not in ("X", "o")
        ]
        if not choices:
            raise RuntimeError("No valid moves left")
        r, c = self.rng.choice(choices)
        return engine.take_turn(r, c)
