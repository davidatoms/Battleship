"""Single- and multi-player game modes.

These are stubs.  Each subclass is expected to wrap an
:class:`~src.game.engine.Engine` with input/output appropriate to its
medium (CLI prompts, AI policies, network sockets, ...).
"""

from __future__ import annotations

from typing import Optional

from .engine import Engine


class GameMode:
    """Base class for all game modes."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def run(self) -> Optional[int]:
        """Drive the game loop until completion; return the winner index."""
        raise NotImplementedError


class TwoPlayerLocal(GameMode):
    """Hot-seat 2-player game on a single machine."""

    def run(self) -> Optional[int]:
        raise NotImplementedError("TwoPlayerLocal.run is not implemented yet")


class SinglePlayerVsAI(GameMode):
    """Single-player game against a built-in AI opponent."""

    def run(self) -> Optional[int]:
        raise NotImplementedError("SinglePlayerVsAI.run is not implemented yet")
