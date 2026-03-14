from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from di_market_manager.config import Config
from di_market_manager.vision import load_templates


@dataclass
class SnapshotResult:
    """Result of a snapshot action."""

    path: str
    scores: dict[str, float]
    visible: list[str]


class Session:
    """Holds config, loaded templates, and an ephemeral action log for a CLI invocation."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.log: list[dict] = []
        load_templates(config)

    def record(self, action: str, **fields: object) -> dict:
        """Append an entry to the ephemeral action log and return it."""
        entry = {"action": action, "timestamp": datetime.now().isoformat(), **fields}
        self.log.append(entry)
        return entry
