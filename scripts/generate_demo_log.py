"""Play a fully-scripted Battleship game and write its JSON log to disk.

Used to produce a deterministic input for the phi-based-fractals
probability-field visualiser.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rules import default_rules, fleet_specs_as_json  # noqa: E402
from src.game.engine import Engine  # noqa: E402
from src.game.log import GameLog  # noqa: E402
from src.setup import Setup  # noqa: E402
from src.ship import EAST, NORTH, SOUTH, WEST  # noqa: E402

CARDINALS = (NORTH, EAST, SOUTH, WEST)


def auto_place(setup: Setup, rng: random.Random, *, log: GameLog, player: int, name: str) -> None:
    while not setup.done:
        ship = setup.current_ship
        assert ship is not None
        for _ in range(500):
            ship.orientation = rng.choice(CARDINALS)
            ship.anchor = (rng.randrange(setup.board.size), rng.randrange(setup.board.size))
            if setup.board.can_place(ship):
                setup.cursor = ship.anchor
                cells = ship.cells()
                if setup.commit_ship():
                    log.append(
                        "placement",
                        player=player, player_name=name,
                        ship=ship.name, length=ship.length,
                        anchor=list(ship.anchor), orientation=ship.orientation,
                        cells=[list(c) for c in cells],
                        method="auto",
                    )
                    break


def play(seed: int, output: Path) -> Path:
    rng = random.Random(seed)
    log = GameLog()
    session_rules = default_rules()
    log.append(
        "game_start",
        players=["Alice", "Bob"],
        size=session_rules.board_size,
        mode="demo",
        fleet=fleet_specs_as_json(session_rules),
    )
    setups = [Setup(rules=session_rules), Setup(rules=session_rules)]
    auto_place(setups[0], rng, log=log, player=0, name="Alice")
    auto_place(setups[1], rng, log=log, player=1, name="Bob")
    boards = [setups[0].board, setups[1].board]
    engine = Engine(boards=boards, log=log, player_names=["Alice", "Bob"])

    while not engine.is_over():
        size = engine.boards[0].size
        target_board = engine.boards[1 - engine.current]
        choices = [
            (r, c)
            for r in range(size)
            for c in range(size)
            if target_board.cell(r, c) not in ("X", "o")
        ]
        if not choices:
            break
        engine.take_turn(*rng.choice(choices))

    output.parent.mkdir(parents=True, exist_ok=True)
    log.save(output)
    print(
        f"Wrote {output} ({len(log)} events, "
        f"winner={engine.winner()}, history={len(engine.history)} shots)"
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic Battleship game log.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "phi-based-fractals" / "outputs" / "battleship" / "demo_game.log.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    play(args.seed, args.output)
