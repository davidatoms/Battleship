"""Structured JSON event log for Battleship games.

Every event is a plain dict and is appended in order.  The minimal
schema is::

    {
      "type":      str,   # "game_start" | "placement" | "turn" | "game_end" | ...
      "timestamp": str,   # ISO-8601 UTC, millisecond precision
      ...                 # event-specific payload
    }

A :class:`GameLog` can be serialised to JSON, saved to disk, and
reloaded for replay or analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Union


PathLike = Union[str, Path]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class GameLog:
    """Append-only event log for a single game."""

    events: List[Dict[str, Any]] = field(default_factory=list)
    version: int = 1

    def append(self, event_type: str, **fields: Any) -> Dict[str, Any]:
        event: Dict[str, Any] = {
            "type": event_type,
            "timestamp": _now_iso(),
        }
        event.update(fields)
        self.events.append(event)
        return event

    def to_dict(self) -> Dict[str, Any]:
        return {"version": self.version, "events": list(self.events)}

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: PathLike) -> Path:
        target = Path(path)
        if target.parent and not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: PathLike) -> "GameLog":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "events" not in data:
            raise ValueError("not a Battleship log file")
        return cls(
            events=list(data.get("events", [])),
            version=int(data.get("version", 1)),
        )

    def filter(self, event_type: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e.get("type") == event_type]

    def has(self, event_type: str) -> bool:
        return any(e.get("type") == event_type for e in self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.events)
