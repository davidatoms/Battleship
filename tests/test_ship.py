import pytest

from src.ship import (
    EAST,
    NORTH,
    NORTH_EAST,
    SOUTH,
    WEST,
    Battleship,
    Carrier,
    Cruiser,
    Destroyer,
    Ship,
    Submarine,
    standard_fleet,
)


def test_standard_fleet_lengths():
    fleet = standard_fleet()
    assert [s.name for s in fleet] == [
        "Carrier", "Battleship", "Cruiser", "Submarine", "Destroyer",
    ]
    assert [s.length for s in fleet] == [5, 4, 3, 3, 2]


def test_no_anchor_means_no_cells():
    ship = Cruiser()
    assert ship.cells() == []


def test_cells_east():
    ship = Carrier(orientation=EAST, anchor=(0, 0))
    assert ship.cells() == [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]


def test_cells_south():
    ship = Battleship(orientation=SOUTH, anchor=(2, 3))
    assert ship.cells() == [(2, 3), (3, 3), (4, 3), (5, 3)]


def test_cells_north_and_west():
    ship_n = Destroyer(orientation=NORTH, anchor=(5, 5))
    assert ship_n.cells() == [(5, 5), (4, 5)]
    ship_w = Destroyer(orientation=WEST, anchor=(5, 5))
    assert ship_w.cells() == [(5, 5), (5, 4)]


def test_cells_diagonal():
    ship = Submarine(orientation=NORTH_EAST, anchor=(4, 4))
    assert ship.cells() == [(4, 4), (3, 5), (2, 6)]


def test_invalid_orientation_raises():
    with pytest.raises(ValueError):
        Ship(name="Bad", length=2, orientation=37)


def test_zero_length_raises():
    with pytest.raises(ValueError):
        Ship(name="Empty", length=0)


def test_hit_at_and_sunk():
    ship = Destroyer(orientation=EAST, anchor=(1, 1))
    assert not ship.is_sunk()
    assert ship.hit_at(1, 1) is True
    assert ship.hit_at(9, 9) is False
    assert not ship.is_sunk()
    assert ship.hit_at(1, 2) is True
    assert ship.is_sunk()
