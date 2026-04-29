import pytest

from src.setup import Setup
from src.ship import EAST, NORTH, SOUTH, WEST


def test_readme_example_runs():
    setup = Setup()
    setup.move_cursor("right")
    setup.rotate_current("d")
    assert setup.commit_ship() is True
    rendered = setup.board.render()
    assert "S" in rendered


def test_cursor_clamps_to_board():
    setup = Setup()
    for _ in range(20):
        setup.move_cursor("up")
        setup.move_cursor("left")
    assert setup.cursor == (0, 0)
    for _ in range(20):
        setup.move_cursor("down")
        setup.move_cursor("right")
    assert setup.cursor == (setup.board.size - 1, setup.board.size - 1)


def test_rotate_keys_change_orientation():
    setup = Setup()
    ship = setup.current_ship
    setup.rotate_current("w")
    assert ship.orientation == NORTH
    setup.rotate_current("d")
    assert ship.orientation == EAST
    setup.rotate_current("s")
    assert ship.orientation == SOUTH
    setup.rotate_current("a")
    assert ship.orientation == WEST


def test_unknown_direction_raises():
    setup = Setup()
    with pytest.raises(ValueError):
        setup.move_cursor("diagonal")


def test_unknown_rotate_key_raises():
    setup = Setup()
    with pytest.raises(ValueError):
        setup.rotate_current("q")


def test_commit_advances_to_next_ship():
    setup = Setup()
    first = setup.current_ship
    assert first is not None
    setup.rotate_current("d")
    assert setup.commit_ship() is True
    assert setup.current_ship is not first
    assert setup.placed == [first]


def test_commit_fails_when_out_of_bounds():
    setup = Setup()
    for _ in range(setup.board.size):
        setup.move_cursor("right")
    setup.rotate_current("d")
    assert setup.commit_ship() is False


def test_commit_fails_on_overlap():
    setup = Setup()
    setup.rotate_current("d")
    assert setup.commit_ship() is True
    setup.rotate_current("d")
    assert setup.commit_ship() is False


def test_place_full_fleet():
    setup = Setup()
    rows_for_each = [0, 2, 4, 6, 8]
    for row in rows_for_each:
        setup.cursor = (row, 0)
        if setup.current_ship is not None:
            setup.current_ship.anchor = setup.cursor
        setup.rotate_current("d")
        assert setup.commit_ship() is True
    assert setup.done is True
    assert len(setup.board.ships) == 5
