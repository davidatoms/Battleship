"""Command-line front-end for the Battleship engine.

Run from the project root:

    python battleship_cli.py

Two game modes are supported:

* hot-seat: two humans share the terminal and pass the keyboard between
  turns.
* vs-AI:    one human plays against a simple random-shooting AI.

During fleet placement, the active ship is shown as ``+`` characters and
the cursor as ``@``.  Commands are typed and submitted with Enter.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.board import Board  # noqa: E402
from src.game.engine import Engine  # noqa: E402
from src.game.log import GameLog  # noqa: E402
from src.setup import Setup  # noqa: E402
from src.ship import EAST, NORTH, SOUTH, WEST  # noqa: E402

CARDINAL_ORIENTATIONS = (NORTH, EAST, SOUTH, WEST)


PLACEMENT_HELP = """\
Placement controls:
  up / down / left / right   move cursor
  w / a / s / d              rotate ship (north / west / south / east)
  place  (or p, enter)       commit the current ship
  auto                       auto-place all remaining ships randomly
  show                       redraw the board
  help                       show this help
  quit                       exit the game
"""


SHOOT_HELP = """\
Shooting controls:
  <coord>      e.g. A5, b7, J10  (column letter + row number)
  show         redraw the boards
  help         show this help
  quit         exit the game
"""


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def prompt(label: str) -> str:
    try:
        return input(label).strip()
    except EOFError:
        return "quit"


def choose_mode() -> str:
    print("Battleship")
    print("==========")
    print("  1) Hot-seat (two humans on this machine)")
    print("  2) Single player vs. AI")
    while True:
        choice = prompt("Choose mode [1/2]: ").lower()
        if choice in ("1", "hot-seat", "hotseat", "h"):
            return "hot-seat"
        if choice in ("2", "ai", "vs-ai", "computer", "c"):
            return "vs-ai"
        if choice in ("quit", "q", "exit"):
            sys.exit(0)
        print("Please enter 1 or 2.")


def auto_place(
    setup: Setup,
    rng: Optional[random.Random] = None,
    *,
    log: Optional[GameLog] = None,
    player: Optional[int] = None,
    player_name: Optional[str] = None,
) -> None:
    """Randomly place every remaining ship and optionally log each placement."""
    rng = rng or random.Random()
    size = setup.board.size
    while not setup.done:
        ship = setup.current_ship
        assert ship is not None
        for _ in range(500):
            ship.orientation = rng.choice(CARDINAL_ORIENTATIONS)
            ship.anchor = (rng.randrange(size), rng.randrange(size))
            if setup.board.can_place(ship):
                setup.cursor = ship.anchor
                cells = ship.cells()
                if setup.commit_ship():
                    if log is not None:
                        log.append(
                            "placement",
                            player=player,
                            player_name=player_name,
                            ship=ship.name,
                            length=ship.length,
                            anchor=list(ship.anchor),
                            orientation=ship.orientation,
                            cells=[list(c) for c in cells],
                            method="auto",
                        )
                    break
        else:
            raise RuntimeError(f"could not auto-place {ship.name}")


def render_placement(setup: Setup, player_name: str) -> None:
    ship = setup.current_ship
    print(f"\n{player_name}'s placement")
    print("-" * (len(player_name) + 12))
    print(setup.render())
    if ship is not None:
        valid = "OK" if setup.can_commit() else "blocked"
        print(
            f"\nNow placing: {ship.name} (length {ship.length}) "
            f"orientation {ship.orientation} -- {valid}"
        )
        print("Type 'help' for controls.")


def human_placement(
    player_name: str,
    *,
    log: Optional[GameLog] = None,
    player: Optional[int] = None,
) -> Board:
    setup = Setup()
    print(f"\n{player_name}, place your fleet. Type 'auto' for random placement.")
    while not setup.done:
        render_placement(setup, player_name)
        cmd = prompt("> ").lower()
        if cmd in ("", "p", "place", "enter"):
            ship = setup.current_ship
            cells = list(ship.cells()) if ship is not None else []
            if not setup.commit_ship():
                print("Cannot place there: out of bounds or overlapping.")
            elif log is not None and ship is not None:
                log.append(
                    "placement",
                    player=player,
                    player_name=player_name,
                    ship=ship.name,
                    length=ship.length,
                    anchor=list(ship.anchor),
                    orientation=ship.orientation,
                    cells=[list(c) for c in cells],
                    method="manual",
                )
            continue
        if cmd in ("up", "down", "left", "right"):
            setup.move_cursor(cmd)
            continue
        if cmd in ("w", "a", "s", "d"):
            setup.rotate_current(cmd)
            continue
        if cmd == "auto":
            auto_place(setup, log=log, player=player, player_name=player_name)
            continue
        if cmd == "show":
            continue
        if cmd in ("help", "?"):
            print(PLACEMENT_HELP)
            continue
        if cmd in ("quit", "q", "exit"):
            sys.exit(0)
        print(f"Unknown command: {cmd!r}. Type 'help' for the controls.")
    print(f"\n{player_name}'s fleet is set.")
    print(setup.board.render())
    return setup.board


def ai_placement(
    rng: Optional[random.Random] = None,
    *,
    log: Optional[GameLog] = None,
    player: Optional[int] = None,
    player_name: Optional[str] = None,
) -> Board:
    setup = Setup()
    auto_place(setup, rng, log=log, player=player, player_name=player_name)
    return setup.board


def parse_coord(text: str, size: int) -> Optional[Tuple[int, int]]:
    """Parse a coordinate string like 'A5' or 'a 10' into (row, col)."""
    cleaned = text.strip().upper().replace(" ", "")
    if not cleaned:
        return None
    letters = ""
    digits = ""
    i = 0
    while i < len(cleaned) and cleaned[i].isalpha():
        letters += cleaned[i]
        i += 1
    while i < len(cleaned) and cleaned[i].isdigit():
        digits += cleaned[i]
        i += 1
    if i != len(cleaned) or not letters or not digits:
        return None
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    col -= 1
    row = int(digits) - 1
    if not (0 <= row < size and 0 <= col < size):
        return None
    return (row, col)


def render_battle(
    boards: List[Board],
    names: List[str],
    current: int,
    *,
    hide_self: bool = False,
) -> None:
    own = boards[current]
    opp = boards[1 - current]
    print(f"\n{names[current]}'s turn")
    print("-" * (len(names[current]) + 7))
    print(f"\n{names[1 - current]}'s board (your shots):")
    print(opp.render(hidden=True))
    print(f"\n{names[current]}'s board (your fleet):")
    print(own.render(hidden=hide_self))


def shot_summary(result, names: List[str]) -> str:
    shooter = names[result.shooter]
    r, c = result.target
    coord = f"{Board._column_label(c)}{r + 1}"
    if result.outcome == "sunk":
        return f"{shooter} fired at {coord} -- SUNK the {result.sunk_ship}!"
    if result.outcome == "hit":
        return f"{shooter} fired at {coord} -- HIT."
    if result.outcome == "miss":
        return f"{shooter} fired at {coord} -- miss."
    if result.outcome == "already":
        return f"{shooter} already fired at {coord}."
    return f"{shooter} input was invalid."


def human_turn(engine: Engine, names: List[str]) -> None:
    size = engine.boards[0].size
    while True:
        render_battle(engine.boards, names, engine.current)
        cmd = prompt(f"{names[engine.current]}, target> ").lower()
        if cmd in ("quit", "q", "exit"):
            sys.exit(0)
        if cmd in ("help", "?"):
            print(SHOOT_HELP)
            continue
        if cmd == "show":
            continue
        coord = parse_coord(cmd, size)
        if coord is None:
            print("Invalid coordinate. Use a column letter + row number, e.g. B7.")
            continue
        result = engine.take_turn(*coord)
        print(shot_summary(result, names))
        if result.outcome in ("invalid", "already"):
            continue
        return


def ai_turn(engine: Engine, names: List[str], rng: random.Random) -> None:
    size = engine.boards[0].size
    own_idx = engine.current
    target_board = engine.boards[1 - own_idx]
    while True:
        choices = [
            (r, c)
            for r in range(size)
            for c in range(size)
            if target_board.cell(r, c) not in ("X", "o")
        ]
        if not choices:
            return
        r, c = rng.choice(choices)
        result = engine.take_turn(r, c)
        print(shot_summary(result, names))
        if result.outcome not in ("invalid", "already"):
            return


def play(mode: str, *, log: Optional[GameLog] = None, seed: Optional[int] = None) -> None:
    rng = random.Random(seed)
    if mode == "hot-seat":
        names = ["Player 1", "Player 2"]
        if log is not None:
            log.append("game_start", mode=mode, players=list(names), size=Board.DEFAULT_SIZE)
        clear_screen()
        board1 = human_placement(names[0], log=log, player=0)
        prompt("\nPress Enter to hand the keyboard to Player 2...")
        clear_screen()
        board2 = human_placement(names[1], log=log, player=1)
        prompt("\nPress Enter to start the battle...")
        clear_screen()
        boards = [board1, board2]
        is_human = [True, True]
    else:
        names = ["Player", "Computer"]
        if log is not None:
            log.append("game_start", mode=mode, players=list(names), size=Board.DEFAULT_SIZE)
        clear_screen()
        board_human = human_placement(names[0], log=log, player=0)
        board_ai = ai_placement(rng, log=log, player=1, player_name=names[1])
        prompt("\nPress Enter to start the battle...")
        clear_screen()
        boards = [board_human, board_ai]
        is_human = [True, False]

    engine = Engine(boards=boards, log=log, player_names=list(names))

    while not engine.is_over():
        if is_human[engine.current]:
            human_turn(engine, names)
        else:
            print(f"\n{names[engine.current]}'s turn")
            ai_turn(engine, names, rng)
        if mode == "hot-seat" and not engine.is_over():
            prompt(f"\nPress Enter to hand the keyboard to {names[engine.current]}...")
            clear_screen()

    winner = engine.winner()
    print("\n" + "=" * 40)
    print(f"Game over! {names[winner]} wins.")
    print("=" * 40)
    print(f"\n{names[0]}'s board:")
    print(boards[0].render())
    print(f"\n{names[1]}'s board:")
    print(boards[1].render())


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play Battleship in the terminal.")
    parser.add_argument(
        "--log",
        type=Path,
        help="Write a JSON log of the game to this path on exit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional RNG seed for reproducible AI / auto-placement.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    log = GameLog() if args.log is not None else None
    try:
        mode = choose_mode()
        play(mode, log=log, seed=args.seed)
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
        if log is not None and args.log is not None:
            log.append("interrupted")
            log.save(args.log)
            print(f"Partial log saved to {args.log}")
        return 130
    finally:
        if log is not None and args.log is not None and not log.has("interrupted"):
            log.save(args.log)
            print(f"\nLog saved to {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
