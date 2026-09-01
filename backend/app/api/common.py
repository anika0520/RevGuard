"""Shared response envelope so every payload is self-describing."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..store.memory import store


def ok(data: Any, **meta: Any) -> dict[str, Any]:
    cfg = get_settings()
    return {
        "data": data,
        "meta": {
            "generated_at": store.now().isoformat(),
            "sim_clock": store.now().isoformat(),
            "source": "mock" if cfg.demo_mode else "live",
            "version": cfg.version,
            **meta,
        },
    }
