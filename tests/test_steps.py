import csv
import json
from pathlib import Path

import pytest

from src.board import Board
from src.game.engine import Engine
from src.game.log import GameLog
from src.ship import Destroyer, EAST


def _setup_engine_with_log() -> tuple[Engine, GameLog]:
    log = GameLog()
    log.append("game_start", players=["A", "B"], size=10, mode="hot-seat")
    boards = []
    for player, anchor in ((0, (0, 0)), (1, (5, 5))):
        b = Board()
        ship = Destroyer(orientation=EAST, anchor=anchor)
        b.place_ship(ship)
        boards.append(b)
        log.append(
            "placement",
            player=player,
            player_name=f"P{player}",
            ship=ship.name,
            length=ship.length,
            anchor=list(ship.anchor),
            orientation=ship.orientation,
            cells=[list(c) for c in ship.cells()],
        )
    return Engine(boards=boards, log=log, player_names=["A", "B"]), log


def test_export_step_index_writes_csv_pngs_and_manifest(tmp_path: Path):
    pytest.importorskip("matplotlib")

    from src.analysis.steps import CSV_COLUMNS, export_step_index

    engine, log = _setup_engine_with_log()
    engine.take_turn(0, 0)
    engine.take_turn(5, 5)
    engine.take_turn(5, 5)
    engine.take_turn(0, 0)
    engine.take_turn(5, 6)
    engine.take_turn(0, 1)

    csv_path, manifest_path = export_step_index(log, tmp_path, resolution=80)
    assert csv_path == tmp_path / "steps.csv"
    assert manifest_path == tmp_path / "steps_manifest.json"
    assert csv_path.exists()
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["kind"] == "step_heatmaps"
    assert data["truncated"] is False
    assert "rows" in data and isinstance(data["rows"], list)

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        assert reader.fieldnames == list(CSV_COLUMNS)

    assert len(rows) >= 6
    assert len(data["rows"]) == len(rows)

    for row in rows:
        for col in ("hit_path", "miss_path", "actual_path"):
            assert row[col]
            png = tmp_path / row[col]
            assert png.exists()
            assert png.stat().st_size > 0
        if row["outcome"] in ("hit", "sunk"):
            assert row["actual_path"] == row["hit_path"]
        elif row["outcome"] == "miss":
            assert row["actual_path"] == row["miss_path"]


def test_export_step_index_manifest_matches_csv_rows(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from src.analysis.steps import export_step_index

    engine, log = _setup_engine_with_log()
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)

    _, manifest_path = export_step_index(log, tmp_path, resolution=80)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["rows"][0]["turn"] == 1
    assert data["rows"][0]["hit_path"].startswith("step_")


def test_export_step_index_with_no_prior(tmp_path: Path):
    pytest.importorskip("matplotlib")

    from src.analysis.steps import export_step_index

    engine, log = _setup_engine_with_log()
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)

    csv_path, _ = export_step_index(log, tmp_path, include_prior=False, resolution=80)
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    for row in rows:
        assert row["prior_path"] == ""
        assert not (tmp_path / f"step_{int(row['turn']):03d}_prior.png").exists()
        assert (tmp_path / row["hit_path"]).exists()
        assert (tmp_path / row["miss_path"]).exists()


def test_export_step_index_handles_empty_log(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from src.analysis.steps import export_step_index

    csv_path, manifest_path = export_step_index(GameLog(), tmp_path)
    assert csv_path.exists()
    assert manifest_path.exists()
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows == []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["rows"] == []
    assert data["exported_rows"] == 0


def test_export_step_index_max_steps_truncates(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from src.analysis.steps import export_step_index

    engine, log = _setup_engine_with_log()
    engine.take_turn(0, 0)
    engine.take_turn(5, 5)
    engine.take_turn(5, 5)
    engine.take_turn(0, 0)
    engine.take_turn(5, 6)
    engine.take_turn(0, 1)

    csv_path, manifest_path = export_step_index(log, tmp_path, max_steps=2, resolution=80)
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["exported_rows"] == 2
    assert data["truncated"] is True
    assert data["options"]["max_steps"] == 2


def test_export_step_index_max_steps_high_no_truncation(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from src.analysis.steps import export_step_index

    engine, log = _setup_engine_with_log()
    engine.take_turn(0, 0)
    engine.take_turn(9, 9)

    _, manifest_path = export_step_index(log, tmp_path, max_steps=999, resolution=80)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["truncated"] is False


def test_export_step_index_invalid_max_steps(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from src.analysis.steps import export_step_index

    with pytest.raises(ValueError):
        export_step_index(GameLog(), tmp_path, max_steps=0)
