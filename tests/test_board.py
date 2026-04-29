import pytest

from src.board import Board
from src.ship import EAST, SOUTH, Carrier, Destroyer


def test_default_size_is_ten():
    b = Board()
    assert b.size == 10
    assert all(b.cell(r, c) == "." for r in range(10) for c in range(10))


def test_invalid_size_raises():
    with pytest.raises(ValueError):
        Board(size=0)


def test_in_bounds():
    b = Board()
    assert b.in_bounds(0, 0)
    assert b.in_bounds(9, 9)
    assert not b.in_bounds(-1, 0)
    assert not b.in_bounds(10, 0)


def test_place_ship_succeeds_in_bounds():
    b = Board()
    ship = Carrier(orientation=EAST, anchor=(0, 0))
    assert b.place_ship(ship) is True
    assert all(b.is_occupied(0, c) for c in range(5))


def test_place_ship_rejects_out_of_bounds():
    b = Board()
    ship = Carrier(orientation=EAST, anchor=(0, 6))
    assert b.place_ship(ship) is False
    assert not any(b.is_occupied(0, c) for c in range(10))


def test_place_ship_rejects_overlap():
    b = Board()
    a = Carrier(orientation=EAST, anchor=(0, 0))
    overlap = Destroyer(orientation=SOUTH, anchor=(0, 2))
    assert b.place_ship(a) is True
    assert b.place_ship(overlap) is False


def test_receive_shot_outcomes():
    b = Board()
    b.place_ship(Destroyer(orientation=EAST, anchor=(4, 4)))
    assert b.receive_shot(0, 0) == "miss"
    assert b.receive_shot(4, 4) == "hit"
    assert b.receive_shot(4, 4) == "already"
    assert b.receive_shot(-1, 0) == "invalid"


def test_all_sunk():
    b = Board()
    ship = Destroyer(orientation=EAST, anchor=(0, 0))
    b.place_ship(ship)
    assert not b.all_sunk()
    b.receive_shot(0, 0)
    b.receive_shot(0, 1)
    assert b.all_sunk()


def test_render_has_headers_and_grid():
    b = Board()
    rendered = b.render()
    lines = rendered.splitlines()
    assert lines[0].strip().startswith("A B C")
    assert lines[1].lstrip().startswith("1 ")
    assert lines[-1].lstrip().startswith("10 ")


def test_render_hides_ships_when_requested():
    b = Board()
    b.place_ship(Destroyer(orientation=EAST, anchor=(0, 0)))
    visible = b.render()
    hidden = b.render(hidden=True)
    assert "S" in visible
    assert "S" not in hidden
