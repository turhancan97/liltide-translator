"""Session events independent of provider and terminal implementation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Gap:
    start_ms: int
    end_ms: int
    reason: str
