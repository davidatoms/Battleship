"""Reconstruct shooter's-view board state from a JSON game log."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..board import Board
from ..rules import house_rules_from_events, partition_fleet_after_sinks
from .probability import MISS, OPEN_HIT, SUNK, UNKNOWN


def _opponent_ships(
    events: Sequence[Dict[str, Any]], opponent: int
) -> Dict[str, List[Tuple[int, int]]]:
    """Map ship name -> ordered list of (row, col) cells for opponent placements."""
    out: Dict[str, List[Tuple[int, int]]] = {}
    for ev in events:
        if ev.get("type") != "placement":
            continue
        if ev.get("player") != opponent:
            continue
        cells = [tuple(c) for c in ev.get("cells", [])]
        out[str(ev.get("ship"))] = cells
    return out


def replay_state(
    events: Sequence[Dict[str, Any]],
    up_to_index: Optional[int],
    shooter: int,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """Reconstruct what ``shooter`` knows about the opponent's board.

    Returns
    -------
    view :
        ``(size, size)`` array of markers (UNKNOWN / MISS / OPEN_HIT /
        SUNK) from the shooter's perspective.
    alive_lengths :
        Lengths of opponent ships still afloat.
    sunk_lengths :
        Lengths of opponent ships already sunk by the shooter.
    """
    if up_to_index is None:
        up_to_index = len(events)
    truncated = list(events[: max(0, up_to_index)])

    rules = house_rules_from_events(events)
    size = rules.board_size
    view = np.full((size, size), UNKNOWN, dtype="<U1")

    opponent = 1 - shooter
    opp_ships = _opponent_ships(events, opponent)

    sunk_names: List[str] = []
    for ev in truncated:
        if ev.get("type") != "turn":
            continue
        if ev.get("shooter") != shooter:
            continue
        target = ev.get("target")
        if not target or len(target) != 2:
            continue
        r, c = int(target[0]), int(target[1])
        if not (0 <= r < size and 0 <= c < size):
            continue
        outcome = ev.get("outcome")
        if outcome == "miss":
            view[r, c] = MISS
        elif outcome == "hit":
            if view[r, c] != SUNK:
                view[r, c] = OPEN_HIT
        elif outcome == "sunk":
            ship_name = ev.get("sunk_ship")
            if ship_name:
                sunk_names.append(str(ship_name))
            if ship_name and opp_ships and str(ship_name) in opp_ships:
                for rr, cc in opp_ships[str(ship_name)]:
                    if 0 <= rr < size and 0 <= cc < size:
                        view[rr, cc] = SUNK
            else:
                view[r, c] = SUNK

    alive: List[int] = []
    sunk: List[int] = []
    if opp_ships:
        pending = Counter(sunk_names)
        for name, cells in opp_ships.items():
            if pending.get(name, 0) > 0:
                sunk.append(len(cells))
                pending[name] -= 1
            else:
                alive.append(len(cells))
    else:
        sunk_specs, alive_specs = partition_fleet_after_sinks(rules, sunk_names)
        sunk = [s.length for s in sunk_specs]
        alive = sorted((s.length for s in alive_specs), reverse=True)

    return view, alive, sunk


def build_view_from_board(
    own_board: Board,
    opponent_board: Board,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """Build a shooter's-view array directly from two live :class:`Board` objects.

    Useful for live visualisation during a running game without
    serialising to a log first.
    """
    size = opponent_board.size
    view = np.full((size, size), UNKNOWN, dtype="<U1")
    sunk_cells = set()
    sunk_lengths: List[int] = []
    alive_lengths: List[int] = []
    for ship in opponent_board.ships:
        if ship.is_sunk():
            sunk_lengths.append(ship.length)
            for cell in ship.cells():
                sunk_cells.add(cell)
        else:
            alive_lengths.append(ship.length)

    for r in range(size):
        for c in range(size):
            ch = opponent_board.cell(r, c)
            if ch == "X":
                view[r, c] = SUNK if (r, c) in sunk_cells else OPEN_HIT
            elif ch == "o":
                view[r, c] = MISS
    return view, alive_lengths, sunk_lengths
