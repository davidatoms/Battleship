import pytest

from src.board import Board
from src.game.engine import Engine
from src.ship import EAST, Destroyer


def _board_with_destroyer(anchor=(0, 0)):
    board = Board()
    board.place_ship(Destroyer(orientation=EAST, anchor=anchor))
    return board


def test_engine_requires_two_boards():
    with pytest.raises(ValueError):
        Engine(boards=[Board()])


def test_take_turn_alternates_players():
    engine = Engine(boards=[_board_with_destroyer(), _board_with_destroyer()])
    assert engine.current == 0
    engine.take_turn(5, 5)
    assert engine.current == 1
    engine.take_turn(5, 5)
    assert engine.current == 0


def test_invalid_shot_does_not_pass_turn():
    engine = Engine(boards=[_board_with_destroyer(), _board_with_destroyer()])
    result = engine.take_turn(-1, 0)
    assert result.outcome == "invalid"
    assert engine.current == 0


def test_sinking_ship_reports_outcome_and_winner():
    engine = Engine(boards=[_board_with_destroyer(), _board_with_destroyer()])
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)
    result = engine.take_turn(0, 1)
    assert result.outcome == "sunk"
    assert result.sunk_ship == "Destroyer"
    assert engine.winner() == 0
    assert engine.is_over()
