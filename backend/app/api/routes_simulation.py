"""Simulation control + SSE stream."""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Body, Request
from sse_starlette.sse import EventSourceResponse

from ..events.bus import bus
from ..simulation import engine
from ..store.memory import store
from .common import ok

router = APIRouter(prefix="/api", tags=["simulation"])


@router.get("/simulation/state")
def sim_state():
    return ok(engine.state())


@router.post("/simulation/start")
def sim_start(speed: int = Body(10, embed=True)):
    return ok(engine.start(speed))


@router.post("/simulation/pause")
def sim_pause():
    return ok(engine.pause())


@router.post("/simulation/seek")
def sim_seek(to: str = Body(..., embed=True)):
    return ok(engine.seek(datetime.fromisoformat(to)))


@router.post("/simulation/reset")
def sim_reset():
    return ok(engine.reset())


@router.post("/simulation/inject")
def sim_inject(
    scenario: str = Body("vast_spike", embed=True),
    campaign_id: str | None = Body(None, embed=True),
):
    result = engine.inject(scenario, campaign_id)
    if result.get("injected"):
        store.run_analysis(result["campaign_id"])
    return ok(result)


@router.post("/simulation/scenario/golden/replay")
def sim_replay_golden():
    return ok(engine.replay_golden())


@router.get("/stream")
async def stream(request: Request):
    queue = bus.subscribe()

    async def publisher():
        try:
            yield {"event": "hello", "data": '{"kind":"connected"}'}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"event": "guardian", "data": message}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            bus.unsubscribe(queue)

    return EventSourceResponse(publisher())
