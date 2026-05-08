from __future__ import annotations

import random
from typing import List, Optional, Tuple

from src.game.engine import Engine, TurnResult

HUNT = "hunt"
TARGET = "target"
DESTROY = "destroy"


class HeuristicAI:
    """
    AI that implements a Hunt-Target-Destroy strategy:
    1. Hunt: Randomly shoot until a hit is found.
    2. Target: Once a hit is found, shoot at adjacent tiles.
    3. Destroy: Once two hits are found, determine the direction and follow it.
    """

    def __init__(self, size: int = 10, seed: Optional[int] = None):
        self.size = size
        self.rng = random.Random(seed)
        self.state = HUNT
        self.first_hit: Optional[Tuple[int, int]] = None
        self.last_hit: Optional[Tuple[int, int]] = None
        self.direction: Optional[Tuple[int, int]] = None  # (dr, dc)
        self.potential_targets: List[Tuple[int, int]] = []
        self.tried_cells: set[Tuple[int, int]] = set()

    def get_neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        neighbors = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                neighbors.append((nr, nc))
        return neighbors

    def take_turn(self, engine: Engine) -> TurnResult:
        r, c = self._choose_move(engine)
        result = engine.take_turn(r, c)
        self.tried_cells.add((r, c))
        self._update_state(result)
        return result

    def _choose_move(self, engine: Engine) -> Tuple[int, int]:
        target_board = engine.boards[1 - engine.current]

        def is_valid(r: int, c: int) -> bool:
            return (r, c) not in self.tried_cells and target_board.cell(r, c) not in ("X", "o")

        if self.state == HUNT:
            choices = [(r, c) for r in range(self.size) for c in range(self.size) if is_valid(r, c)]
            if not choices:
                raise RuntimeError("No valid moves left")
            return self.rng.choice(choices)

        if self.state == TARGET:
            while self.potential_targets:
                target = self.potential_targets.pop(0)
                if is_valid(*target):
                    return target
            self.state = HUNT
            return self._choose_move(engine)

        if self.state == DESTROY:
            dr, dc = self.direction
            r, c = self.last_hit
            nr, nc = r + dr, c + dc

            if 0 <= nr < self.size and 0 <= nc < self.size and is_valid(nr, nc):
                return (nr, nc)

            self.direction = (-dr, -dc)
            dr, dc = self.direction
            r, c = self.first_hit
            nr, nc = r + dr, c + dc

            if 0 <= nr < self.size and 0 <= nc < self.size and is_valid(nr, nc):
                return (nr, nc)

            self.state = TARGET
            self.potential_targets = self.get_neighbors(*self.first_hit)
            return self._choose_move(engine)

        return self.rng.choice([(r, c) for r in range(self.size) for c in range(self.size) if is_valid(r, c)])

    def _update_state(self, result: TurnResult):
        if result.outcome == "sunk":
            self.state = HUNT
            self.first_hit = None
            self.last_hit = None
            self.direction = None
            self.potential_targets = []
        elif result.outcome == "hit":
            if self.state == HUNT:
                self.state = TARGET
                self.first_hit = result.target
                self.last_hit = result.target
                self.potential_targets = self.get_neighbors(*result.target)
                self.rng.shuffle(self.potential_targets)
            elif self.state == TARGET:
                self.state = DESTROY
                r1, c1 = self.first_hit
                r2, c2 = result.target
                self.direction = (r2 - r1, c2 - c1)
                self.last_hit = result.target
            elif self.state == DESTROY:
                self.last_hit = result.target
        elif result.outcome == "miss":
            if self.state == DESTROY:
                dr, dc = self.direction
                self.direction = (-dr, -dc)
                self.last_hit = self.first_hit
