"""Flask web front-end for hot-seat Battleship.

Run from the project root:

    pip install -r requirements.txt
    python -m web.app
    # then open http://127.0.0.1:5000

State is held in process memory (single game, single tab).  Every
action is appended to a :class:`~src.game.log.GameLog`, viewable at
``/api/log`` and downloadable as JSON at ``/api/log/download``.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, render_template, request, send_file  # noqa: E402

from src.board import Board, SHIP_CELL, WATER  # noqa: E402
from src.game.engine import Engine  # noqa: E402
from src.game.log import GameLog  # noqa: E402
from src.setup import Setup  # noqa: E402
from src.ship import EAST, NORTH, SOUTH, WEST  # noqa: E402


CARDINAL_ORIENTATIONS = (NORTH, EAST, SOUTH, WEST)


@dataclass
class GameState:
    phase: str = "idle"  # "idle" | "setup" | "battle" | "ended"
    setups: List[Setup] = field(default_factory=lambda: [Setup(), Setup()])
    placing: int = 0
    engine: Optional[Engine] = None
    log: GameLog = field(default_factory=GameLog)
    player_names: List[str] = field(
        default_factory=lambda: ["Player 1", "Player 2"]
    )

    def reset(self, names: Optional[List[str]] = None) -> None:
        self.phase = "setup"
        self.setups = [Setup(), Setup()]
        self.placing = 0
        self.engine = None
        self.log = GameLog()
        if names is not None:
            self.player_names = list(names)
        self.log.append(
            "game_start",
            mode="hot-seat-web",
            players=list(self.player_names),
            size=self.setups[0].board.size,
        )


_state = GameState()
_state_lock = RLock()


def _serialize_grid(board: Board, *, hidden: bool) -> List[List[str]]:
    grid: List[List[str]] = []
    for r in range(board.size):
        row = []
        for c in range(board.size):
            ch = board.cell(r, c)
            if hidden and ch == SHIP_CELL:
                ch = WATER
            row.append(ch)
        grid.append(row)
    return grid


def _serialize_setup(setup: Setup) -> Dict[str, Any]:
    ship = setup.current_ship
    return {
        "size": setup.board.size,
        "grid": _serialize_grid(setup.board, hidden=False),
        "current_ship": (
            None
            if ship is None
            else {
                "name": ship.name,
                "length": ship.length,
                "orientation": ship.orientation,
            }
        ),
        "remaining": [
            {"name": s.name, "length": s.length} for s in setup.remaining
        ],
        "placed": [{"name": s.name, "length": s.length} for s in setup.placed],
        "done": setup.done,
    }


def _serialize_state() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "phase": _state.phase,
        "placing": _state.placing,
        "player_names": list(_state.player_names),
        "log_length": len(_state.log),
    }
    if _state.phase == "setup":
        out["setup"] = _serialize_setup(_state.setups[_state.placing])
    elif _state.phase in ("battle", "ended"):
        engine = _state.engine
        assert engine is not None
        out["current"] = engine.current
        out["winner"] = engine.winner()
        out["size"] = engine.boards[0].size
        out["boards"] = [
            _serialize_grid(engine.boards[i], hidden=False) for i in range(2)
        ]
        out["opponent_views"] = [
            _serialize_grid(engine.boards[i], hidden=True) for i in range(2)
        ]
        out["fleets"] = [
            [
                {"name": s.name, "length": s.length, "sunk": s.is_sunk()}
                for s in engine.boards[i].ships
            ]
            for i in range(2)
        ]
    return out


def _auto_place(setup: Setup, rng: random.Random) -> List[Dict[str, Any]]:
    placements: List[Dict[str, Any]] = []
    while not setup.done:
        ship = setup.current_ship
        assert ship is not None
        for _ in range(500):
            ship.orientation = rng.choice(CARDINAL_ORIENTATIONS)
            ship.anchor = (
                rng.randrange(setup.board.size),
                rng.randrange(setup.board.size),
            )
            if setup.board.can_place(ship):
                setup.cursor = ship.anchor
                cells = ship.cells()
                if setup.commit_ship():
                    placements.append(
                        {
                            "ship": ship.name,
                            "length": ship.length,
                            "anchor": list(ship.anchor),
                            "orientation": ship.orientation,
                            "cells": [list(c) for c in cells],
                        }
                    )
                    break
        else:
            raise RuntimeError(f"could not auto-place {ship.name}")
    return placements


app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/new_game")
def api_new_game():
    payload = request.get_json(silent=True) or {}
    raw_names = payload.get("names") or ["Player 1", "Player 2"]
    if (
        not isinstance(raw_names, list)
        or len(raw_names) != 2
        or not all(isinstance(n, str) and n.strip() for n in raw_names)
    ):
        return jsonify({"error": "names must be two non-empty strings"}), 400
    with _state_lock:
        _state.reset(names=[n.strip()[:32] for n in raw_names])
    return jsonify(_serialize_state())


@app.post("/api/place_at")
def api_place_at():
    payload = request.get_json(silent=True) or {}
    row = payload.get("row")
    col = payload.get("col")
    orientation = payload.get("orientation")
    with _state_lock:
        if _state.phase != "setup":
            return jsonify({"error": "not in setup phase"}), 400
        setup = _state.setups[_state.placing]
        ship = setup.current_ship
        if ship is None:
            return jsonify({"error": "no ship to place"}), 400
        if not isinstance(row, int) or not isinstance(col, int):
            return jsonify({"error": "row and col must be integers"}), 400
        if orientation is not None and int(orientation) not in CARDINAL_ORIENTATIONS:
            return jsonify({"error": "orientation must be 0, 90, 180, or 270"}), 400
        if orientation is not None:
            ship.orientation = int(orientation)
        ship.anchor = (row, col)
        setup.cursor = (row, col)
        cells = ship.cells()
        if not setup.commit_ship():
            return jsonify({"error": "cannot place there: out of bounds or overlap"}), 400
        _state.log.append(
            "placement",
            player=_state.placing,
            player_name=_state.player_names[_state.placing],
            ship=ship.name,
            length=ship.length,
            anchor=list(ship.anchor) if ship.anchor else None,
            orientation=ship.orientation,
            cells=[list(c) for c in cells],
            method="manual",
        )
        return jsonify(_serialize_state())


@app.post("/api/auto_place")
def api_auto_place():
    with _state_lock:
        if _state.phase != "setup":
            return jsonify({"error": "not in setup phase"}), 400
        setup = _state.setups[_state.placing]
        placements = _auto_place(setup, random.Random())
        for p in placements:
            _state.log.append(
                "placement",
                player=_state.placing,
                player_name=_state.player_names[_state.placing],
                method="auto",
                **p,
            )
        return jsonify(_serialize_state())


@app.post("/api/finish_setup")
def api_finish_setup():
    with _state_lock:
        if _state.phase != "setup":
            return jsonify({"error": "not in setup phase"}), 400
        if not _state.setups[_state.placing].done:
            return jsonify({"error": "current player has not finished placement"}), 400
        if _state.placing == 0:
            _state.placing = 1
            return jsonify(_serialize_state())
        if not _state.setups[1].done:
            return jsonify({"error": "second player not done"}), 400
        _state.engine = Engine(
            boards=[_state.setups[0].board, _state.setups[1].board],
            log=_state.log,
            player_names=list(_state.player_names),
        )
        _state.phase = "battle"
        return jsonify(_serialize_state())


@app.post("/api/shoot")
def api_shoot():
    payload = request.get_json(silent=True) or {}
    row = payload.get("row")
    col = payload.get("col")
    with _state_lock:
        if _state.phase != "battle":
            return jsonify({"error": "not in battle phase"}), 400
        if not isinstance(row, int) or not isinstance(col, int):
            return jsonify({"error": "row and col must be integers"}), 400
        engine = _state.engine
        assert engine is not None
        result = engine.take_turn(row, col)
        if engine.is_over():
            _state.phase = "ended"
        out = _serialize_state()
        out["last_shot"] = {
            "shooter": result.shooter,
            "shooter_name": _state.player_names[result.shooter],
            "target": list(result.target),
            "target_label": f"{Board._column_label(col)}{row + 1}",
            "outcome": result.outcome,
            "sunk_ship": result.sunk_ship,
        }
        return jsonify(out)


@app.get("/api/state")
def api_state():
    with _state_lock:
        return jsonify(_serialize_state())


@app.get("/api/log")
def api_log():
    with _state_lock:
        return jsonify(_state.log.to_dict())


@app.get("/api/log/download")
def api_log_download():
    with _state_lock:
        data = _state.log.to_json().encode("utf-8")
    return send_file(
        BytesIO(data),
        mimetype="application/json",
        as_attachment=True,
        download_name="battleship-log.json",
    )


def main() -> None:
    host = os.environ.get("BATTLESHIP_HOST", "127.0.0.1")
    port = int(os.environ.get("BATTLESHIP_PORT", "5000"))
    print(f"Battleship web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
