"""Opponent shooting strategies (AI players).

Implementations implement :class:`ShootingStrategy`: a single ``take_turn(engine)``
that applies one shot. Training utilities and saved weights remain under ``ml/``.
"""

from __future__ import annotations

from typing import Dict, Type

from .base import ShootingStrategy
from .ensemble import EnsembleAI
from .heuristic import DESTROY, HUNT, TARGET, HeuristicAI
from .hybrid import HybridAI
from .random import RandomShooting
from .rl import RLAgent

STRATEGY_REGISTRY: Dict[str, Type[ShootingStrategy]] = {
    "random": RandomShooting,
    "heuristic": HeuristicAI,
    "rl": RLAgent,
    "hybrid": HybridAI,
    "ensemble": EnsembleAI,
}

__all__ = [
    "ShootingStrategy",
    "STRATEGY_REGISTRY",
    "RandomShooting",
    "HeuristicAI",
    "RLAgent",
    "HybridAI",
    "EnsembleAI",
    "HUNT",
    "TARGET",
    "DESTROY",
]
