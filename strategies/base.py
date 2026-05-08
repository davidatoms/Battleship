"""Shared typing for opponent shooting algorithms."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.game.engine import Engine, TurnResult


@runtime_checkable
class ShootingStrategy(Protocol):
    """Anything that can choose and fire one shot given the current engine."""

    def take_turn(self, engine: Engine) -> TurnResult:
        ...
