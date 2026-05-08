from __future__ import annotations

import numpy as np
from typing import Tuple

from src.analysis.probability import UNKNOWN, OPEN_HIT, MISS, compute_probability_map
from src.game.engine import Engine

from .heuristic import HUNT, HeuristicAI


class HybridAI(HeuristicAI):
    """
    Hybrid AI that uses probability maps for hunting and
    heuristics for targeting/destroying.
    """

    def _choose_move(self, engine: Engine) -> Tuple[int, int]:
        if self.state != HUNT:
            return super()._choose_move(engine)

        target_board = engine.boards[1 - engine.current]

        view = np.full((self.size, self.size), UNKNOWN, dtype=object)
        for r in range(self.size):
            for c in range(self.size):
                cell = target_board.cell(r, c)
                if cell == "o":
                    view[r, c] = MISS
                elif cell == "X":
                    view[r, c] = OPEN_HIT

        alive_lengths = []
        for ship in target_board.ships:
            if not ship.is_sunk():
                alive_lengths.append(ship.length)

        if not alive_lengths:
            return super()._choose_move(engine)

        prob_map = compute_probability_map(view, alive_lengths)

        for r, c in self.tried_cells:
            prob_map[r, c] = -1.0

        max_idx = np.argmax(prob_map)
        r, c = divmod(max_idx, self.size)

        if prob_map[r, c] <= 0:
            return super()._choose_move(engine)

        return (int(r), int(c))
