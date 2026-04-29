import json
from pathlib import Path

import pytest

from src.board import Board
from src.game.engine import Engine
from src.game.log import GameLog
from src.ship import EAST, Destroyer


def test_append_assigns_type_and_timestamp():
    log = GameLog()
    event = log.append("placement", player=0, ship="Carrier")
    assert event["type"] == "placement"
    assert event["player"] == 0
    assert event["ship"] == "Carrier"
    assert "timestamp" in event
    assert len(log) == 1


def test_filter_and_has():
    log = GameLog()
    log.append("turn", outcome="hit")
    log.append("turn", outcome="miss")
    log.append("game_end", winner=0)
    assert len(log.filter("turn")) == 2
    assert log.has("game_end")
    assert not log.has("placement")


def test_save_and_load_round_trip(tmp_path: Path):
    log = GameLog()
    log.append("game_start", players=["A", "B"])
    log.append("turn", shooter=0, target=[0, 0], outcome="miss")
    out = log.save(tmp_path / "log.json")
    assert out.exists()
    raw = json.loads(out.read_text())
    assert raw["version"] == 1
    assert len(raw["events"]) == 2
    reloaded = GameLog.load(out)
    assert len(reloaded) == 2
    assert reloaded.events[0]["type"] == "game_start"


def test_load_rejects_unknown_format(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError):
        GameLog.load(bad)


def _board_with_destroyer(anchor=(0, 0)):
    board = Board()
    board.place_ship(Destroyer(orientation=EAST, anchor=anchor))
    return board


def test_engine_logs_turn_and_game_end():
    log = GameLog()
    engine = Engine(
        boards=[_board_with_destroyer(), _board_with_destroyer()],
        log=log,
        player_names=["Alice", "Bob"],
    )
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)
    engine.take_turn(0, 1)
    turns = log.filter("turn")
    assert len(turns) == 3
    assert turns[0]["outcome"] == "hit"
    assert turns[0]["target_label"] == "A1"
    assert turns[0]["shooter_name"] == "Alice"
    assert turns[2]["outcome"] == "sunk"
    assert turns[2]["sunk_ship"] == "Destroyer"
    end = log.filter("game_end")
    assert len(end) == 1
    assert end[0]["winner"] == 0
    assert end[0]["winner_name"] == "Alice"


def test_engine_does_not_log_invalid_or_double_game_end():
    log = GameLog()
    engine = Engine(
        boards=[_board_with_destroyer(), _board_with_destroyer()],
        log=log,
    )
    engine.take_turn(-1, 0)
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)
    engine.take_turn(0, 1)
    engine.take_turn(5, 5)
    assert len(log.filter("game_end")) == 1
    invalid = [t for t in log.filter("turn") if t["outcome"] == "invalid"]
    assert len(invalid) == 1
