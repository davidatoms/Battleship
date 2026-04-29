import numpy as np

from src.analysis.probability import MISS, OPEN_HIT, SUNK, UNKNOWN
from src.analysis.replay import replay_state
from src.board import Board
from src.game.engine import Engine
from src.game.log import GameLog
from src.ship import Destroyer, EAST


def _build_simple_log() -> GameLog:
    log = GameLog()
    log.append("game_start", players=["Alice", "Bob"], size=10, mode="hot-seat")
    log.append(
        "placement",
        player=0, player_name="Alice",
        ship="Destroyer", length=2,
        anchor=[0, 0], orientation=90,
        cells=[[0, 0], [0, 1]],
    )
    log.append(
        "placement",
        player=1, player_name="Bob",
        ship="Destroyer", length=2,
        anchor=[5, 5], orientation=90,
        cells=[[5, 5], [5, 6]],
    )
    return log


def test_replay_initial_state_is_all_unknown():
    log = _build_simple_log()
    view, alive, sunk = replay_state(list(log.events), up_to_index=None, shooter=0)
    assert view.shape == (10, 10)
    assert (view == UNKNOWN).all()
    assert sorted(alive) == [2]
    assert sunk == []


def test_replay_through_engine_produces_consistent_view():
    boards = []
    log = GameLog()
    log.append("game_start", players=["A", "B"], size=10, mode="hot-seat")
    for player in (0, 1):
        b = Board()
        anchor = (0, 0) if player == 0 else (5, 5)
        ship = Destroyer(orientation=EAST, anchor=anchor)
        b.place_ship(ship)
        boards.append(b)
        log.append(
            "placement",
            player=player, player_name=f"P{player}",
            ship=ship.name, length=ship.length,
            anchor=list(ship.anchor), orientation=ship.orientation,
            cells=[list(c) for c in ship.cells()],
        )

    engine = Engine(boards=boards, log=log, player_names=["A", "B"])
    engine.take_turn(5, 5)  # A hits
    engine.take_turn(0, 0)  # B hits
    engine.take_turn(5, 6)  # A sinks B's destroyer

    events = list(log.events)
    view_a, alive_a, sunk_a = replay_state(events, up_to_index=None, shooter=0)
    view_b, alive_b, sunk_b = replay_state(events, up_to_index=None, shooter=1)

    assert view_a[5, 5] == SUNK
    assert view_a[5, 6] == SUNK
    assert alive_a == []
    assert sunk_a == [2]

    assert view_b[0, 0] == OPEN_HIT
    assert (view_b == MISS).sum() == 0
    assert alive_b == [2]


def test_replay_truncates_at_index():
    log = _build_simple_log()
    log.append(
        "turn",
        shooter=0, shooter_name="Alice",
        target=[5, 5], target_label="F6",
        outcome="hit", sunk_ship=None,
    )
    log.append(
        "turn",
        shooter=1, shooter_name="Bob",
        target=[9, 9], target_label="J10",
        outcome="miss", sunk_ship=None,
    )
    events = list(log.events)
    view_before, _, _ = replay_state(events, up_to_index=3, shooter=0)
    view_after, _, _ = replay_state(events, up_to_index=4, shooter=0)
    assert (view_before == UNKNOWN).all()
    assert view_after[5, 5] == OPEN_HIT
