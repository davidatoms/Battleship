"""Ship dataclass and concrete fleet types.

Orientations are stored as integer degrees measured clockwise from North,
so the 8 valid values cover the four cardinals plus the four diagonals.
The model supports diagonals even though the default key bindings in
:mod:`src.setup` only wire up the cardinals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


NORTH = 0
NORTH_EAST = 45
EAST = 90
SOUTH_EAST = 135
SOUTH = 180
SOUTH_WEST = 225
WEST = 270
NORTH_WEST = 315

VALID_ORIENTATIONS = (
    NORTH, NORTH_EAST, EAST, SOUTH_EAST,
    SOUTH, SOUTH_WEST, WEST, NORTH_WEST,
)

# (delta_row, delta_col) per step along each orientation.
_ORIENTATION_DELTAS = {
    NORTH:      (-1,  0),
    NORTH_EAST: (-1,  1),
    EAST:       ( 0,  1),
    SOUTH_EAST: ( 1,  1),
    SOUTH:      ( 1,  0),
    SOUTH_WEST: ( 1, -1),
    WEST:       ( 0, -1),
    NORTH_WEST: (-1, -1),
}


@dataclass
class Ship:
    """A ship occupying ``length`` consecutive cells in one orientation."""

    name: str
    length: int
    orientation: int = EAST
    anchor: Optional[Tuple[int, int]] = None
    hits: List[bool] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.length <= 0:
            raise ValueError("length must be positive")
        if self.orientation not in _ORIENTATION_DELTAS:
            raise ValueError(
                f"orientation must be one of {list(VALID_ORIENTATIONS)}, "
                f"got {self.orientation!r}"
            )
        if not self.hits:
            self.hits = [False] * self.length
        elif len(self.hits) != self.length:
            raise ValueError("hits length must equal ship length")

    def cells(self) -> List[Tuple[int, int]]:
        """Return the (row, col) cells the ship currently occupies."""
        if self.anchor is None:
            return []
        dr, dc = _ORIENTATION_DELTAS[self.orientation]
        r0, c0 = self.anchor
        return [(r0 + dr * i, c0 + dc * i) for i in range(self.length)]

    def is_sunk(self) -> bool:
        return all(self.hits)

    def hit_at(self, row: int, col: int) -> bool:
        positions = self.cells()
        if (row, col) in positions:
            self.hits[positions.index((row, col))] = True
            return True
        return False


class Carrier(Ship):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "Carrier")
        kwargs.setdefault("length", 5)
        super().__init__(**kwargs)


class Battleship(Ship):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "Battleship")
        kwargs.setdefault("length", 4)
        super().__init__(**kwargs)


class Cruiser(Ship):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "Cruiser")
        kwargs.setdefault("length", 3)
        super().__init__(**kwargs)


class Submarine(Ship):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "Submarine")
        kwargs.setdefault("length", 3)
        super().__init__(**kwargs)


class Destroyer(Ship):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "Destroyer")
        kwargs.setdefault("length", 2)
        super().__init__(**kwargs)


def standard_fleet() -> List[Ship]:
    """Return a fresh standard fleet from :mod:`~src.rules` defaults."""
    from .rules import build_fleet_from_rules, default_rules

    return build_fleet_from_rules(default_rules())
