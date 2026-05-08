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
from src.rules import default_rules, fleet_specs_as_json  # noqa: E402
from src.game.engine import Engine  # noqa: E402
from src.game.log import GameLog  # noqa: E402
from src.setup import Setup  # noqa: E402
from src.ship import EAST, NORTH, SOUTH, WEST  # noqa: E402
from strategies import EnsembleAI, HeuristicAI, HybridAI, RLAgent  # noqa: E402

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
    print("  2) Single player vs. Random AI")
    print("  3) Single player vs. Heuristic AI")
    print("  4) Single player vs. RL Model")
    print("  5) Single player vs. Hybrid (Prob + Heur)")
    print("  6) Single player vs. Ensemble (Multi-Expert)")
    while True:
        choice = prompt("Choose mode [1/2/3/4/5/6]: ").lower()
        if choice in ("1", "hot-seat", "hotseat", "h"):
            return "hot-seat"
        if choice in ("2", "random", "r"):
            return "vs-ai-random"
        if choice in ("3", "heuristic", "he"):
            return "vs-ai-heuristic"
        if choice in ("4", "rl", "ml"):
            return "vs-ai-rl"
        if choice in ("5", "hybrid", "hy"):
            return "vs-ai-hybrid"
        if choice in ("6", "ensemble", "e"):
            return "vs-ai-ensemble"
        if choice in ("quit", "q", "exit"):
            sys.exit(0)
        print("Please enter 1, 2, 3, 4, 5, or 6.")


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
    ai_obj = None
    session_rules = default_rules()
    fleet_snap = fleet_specs_as_json(session_rules)
    board_size = session_rules.board_size
    if mode == "hot-seat":
        names = ["Player 1", "Player 2"]
        if log is not None:
            log.append(
                "game_start",
                mode=mode,
                players=list(names),
                size=board_size,
                fleet=fleet_snap,
            )
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
            log.append(
                "game_start",
                mode=mode,
                players=list(names),
                size=board_size,
                fleet=fleet_snap,
            )
        clear_screen()
        board_human = human_placement(names[0], log=log, player=0)
        board_ai = ai_placement(rng, log=log, player=1, player_name=names[1])
        prompt("\nPress Enter to start the battle...")
        clear_screen()
        boards = [board_human, board_ai]
        is_human = [True, False]
        
        if mode == "vs-ai-heuristic":
            ai_obj = HeuristicAI(seed=seed)
        elif mode == "vs-ai-rl":
            ai_obj = RLAgent(epsilon=0) # No exploration during play
            q_table_path = Path(__file__).parent / "ml" / "q_table.npy"
            if q_table_path.exists():
                ai_obj.load_q_table(str(q_table_path))
            else:
                print("\nWarning: No pre-trained RL model found at ml/q_table.npy.")
                print("The RL agent will play with a blank Q-table.")
        elif mode == "vs-ai-hybrid":
            ai_obj = HybridAI(seed=seed)
        elif mode == "vs-ai-ensemble":
            ai_obj = EnsembleAI(seed=seed)

    engine = Engine(boards=boards, log=log, player_names=list(names))

    while not engine.is_over():
        if is_human[engine.current]:
            human_turn(engine, names)
        else:
            print(f"\n{names[engine.current]}'s turn")
            if ai_obj is not None:
                result = ai_obj.take_turn(engine)
                print(shot_summary(result, names))
            else:
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
    parser.add_argument(
        "--visualize",
        action="store_true",
        help=(
            "After saving the log, also render probability-field PNGs "
            "next to it. Requires --log."
        ),
    )
    parser.add_argument(
        "--viz-dir",
        type=Path,
        default=None,
        help="Override the visualisation output directory (default: <log>-viz/).",
    )
    parser.add_argument(
        "--viz-per-turn",
        action="store_true",
        help="Include a 4-panel figure for each shot (default: aggregate only).",
    )
    parser.add_argument(
        "--viz-max-turns",
        type=int,
        default=20,
        help="Cap the number of per-turn figures.",
    )
    parser.add_argument(
        "--viz-shooter",
        type=int,
        choices=(0, 1),
        default=None,
        help="Restrict per-turn figures to this shooter (0 or 1).",
    )
    parser.add_argument(
        "--viz-resolution",
        type=int,
        default=240,
        help="Pixels per side for the continuous energy fields.",
    )
    parser.add_argument(
        "--viz-3d",
        action="store_true",
        help=(
            "Also render a 360-degree rotating 3-D 'energy well' GIF for "
            "each per-turn frame plus an aggregate well animation."
        ),
    )
    parser.add_argument(
        "--viz-3d-pivot",
        choices=("max_prob", "shot_cell"),
        default="max_prob",
        help=(
            "What to orbit the camera around: 'max_prob' (deepest well "
            "= most-likely ship cell) or 'shot_cell' (the cell actually "
            "fired at that turn)."
        ),
    )
    parser.add_argument(
        "--viz-steps",
        action="store_true",
        help=(
            "Also write a per-step single-panel heatmap for each turn "
            "(prior / if hit / if miss) plus a steps.csv index file "
            "linking each turn's metadata to its image paths."
        ),
    )
    parser.add_argument(
        "--viz-steps-no-prior",
        action="store_true",
        help="With --viz-steps, skip rendering the per-step prior PNG.",
    )
    parser.add_argument(
        "--viz-steps-max",
        type=int,
        default=None,
        help=(
            "Cap how many step rows / PNG sets are written "
            "(default: every eligible turn). Also writes steps_manifest.json."
        ),
    )
    return parser.parse_args(argv)


def _write_visualisations(log: GameLog, log_path: Path, args: argparse.Namespace) -> None:
    from src.analysis.visualize import visualise_log

    viz_dir = args.viz_dir or log_path.with_name(log_path.stem + "-viz")
    print(f"\nRendering visualisations into {viz_dir} ...")
    generated = visualise_log(
        log,
        viz_dir,
        shooter=args.viz_shooter,
        resolution=args.viz_resolution,
        per_turn=args.viz_per_turn,
        max_turns=args.viz_max_turns,
        label=log_path.name,
        well_3d=args.viz_3d,
        well_pivot=args.viz_3d_pivot,
        step_csv=args.viz_steps,
        step_include_prior=not args.viz_steps_no_prior,
        step_max_steps=args.viz_steps_max,
    )
    print(f"Wrote {len(generated)} visualisation(s).")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.visualize and args.log is None:
        print("--visualize requires --log", file=sys.stderr)
        return 2

    # Automatic logging setup
    log_dir = Path("game_logs")
    log_dir.mkdir(exist_ok=True)
    
    if args.log is not None:
        log_path = args.log
    else:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"game_{timestamp}.json"

    log = GameLog()
    try:
        mode = choose_mode()
        play(mode, log=log, seed=args.seed)
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
        log.append("interrupted")
        log.save(log_path)
        print(f"Partial log saved to {log_path}")
        if args.visualize:
            try:
                _write_visualisations(log, log_path, args)
            except Exception as exc:
                print(f"Visualisation failed: {exc}", file=sys.stderr)
        return 130
    finally:
        if not log.has("interrupted"):
            log.save(log_path)
            print(f"\nLog saved to {log_path}")
            if args.visualize:
                try:
                    _write_visualisations(log, log_path, args)
                except Exception as exc:
                    print(f"Visualisation failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
