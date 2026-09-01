"""Tiny async pub/sub feeding the SSE stream."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any

MAX_HISTORY = 300


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self.history: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY)

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subscribers.discard(q)

    def publish(self, kind: str, payload: dict[str, Any]) -> None:
        event = {
            "kind": kind,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self.history.append(event)
        message = json.dumps(event, default=str)
        for q in list(self._subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self.history)[-limit:][::-1]


bus = EventBus()
