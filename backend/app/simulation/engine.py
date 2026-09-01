"""Virtual clock + scenario injection. This is what makes incidents appear live on stage."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import numpy as np

from ..events.bus import bus
from ..store.memory import store
from ..store.world import CAUSE_EFFECT

TICK_SECONDS = 1.0
ANALYSIS_EVERY_SIM_MINUTES = 15

_task: asyncio.Task | None = None
_accumulated = 0.0


def state() -> dict:
    return {
        "sim_clock": store.now().isoformat(),
        "speed": store.speed,
        "running": store.speed > 0,
        "world_start": store.world.origin.isoformat(),
        "world_end": store.world.ts_for(store.world.hours - 1).isoformat(),
        "golden_campaign_id": store.world.golden_id,
        "analysis_runs": store.analysis_runs,
    }


async def _loop() -> None:
    global _accumulated
    while True:
        await asyncio.sleep(TICK_SECONDS)
        if store.speed <= 0:
            continue
        store.advance(store.speed)
        _accumulated += store.speed
        bus.publish("metric.tick", {"sim_clock": store.now().isoformat(), "speed": store.speed})
        if _accumulated >= ANALYSIS_EVERY_SIM_MINUTES:
            _accumulated = 0.0
            await asyncio.to_thread(store.run_analysis)


def ensure_started() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


def start(speed: int) -> dict:
    store.speed = max(1, min(600, speed))
    ensure_started()
    bus.publish("simulation.started", {"speed": store.speed})
    return state()


def pause() -> dict:
    store.speed = 0
    bus.publish("simulation.paused", {"sim_clock": store.now().isoformat()})
    return state()


def seek(ts) -> dict:
    store.set_clock(ts)
    store.run_analysis()
    bus.publish("simulation.seek", {"sim_clock": store.now().isoformat()})
    return state()


def reset() -> dict:
    store.reset()
    return state()


def replay_golden() -> dict:
    """Rewind to just before the Acme cascade, then run the world forward fast."""
    store.reset()
    series = store.world.series[store.world.golden_id]
    onset = store.world.ts_for(series.onset_idx or 0)
    store.set_clock(onset - timedelta(hours=1))
    store.run_analysis()
    bus.publish(
        "simulation.replay",
        {"scenario": "golden", "campaign_id": store.world.golden_id,
         "sim_clock": store.now().isoformat()},
    )
    start(30)
    return state()


SCENARIOS = {
    "vast_spike": ("VAST_PLAYBACK_ERRORS", 0.45),
    "targeting_change": ("TARGETING_RESTRICTION", 0.40),
    "supply_collapse": ("SUPPLY_SHORTAGE", 0.32),
    "auction_squeeze": ("GAM_COMPETITION", 0.55),
}


def inject(scenario: str, campaign_id: str | None = None) -> dict:
    """Degrade a currently-healthy campaign from now onward so the pipeline finds it live."""
    if scenario == "data_outage":
        return _inject_data_outage(campaign_id)

    cause, rate = SCENARIOS.get(scenario, SCENARIOS["vast_spike"])
    target = campaign_id or _pick_healthy()
    s = store.world.series[target]
    n = store.world.idx_for(store.now())
    end = min(store.world.hours, s.fill_end + 1)
    if n >= end:
        return {"injected": False, "reason": "campaign flight has ended"}

    span = np.arange(n, end)
    ramp = np.clip((span - n + 1) / 2.0, 0.0, 1.0)
    fs, es, ivs, ps = CAUSE_EFFECT[cause]
    fill = s.baseline_fill * (1.0 + fs * ramp)
    errate = np.clip(s.baseline_error * (1.0 + es * ramp), 0.0, 0.6)
    target_imps = s.nominal_impressions[span] * (1.0 - (1.0 - rate) * ramp)

    r = target_imps / np.maximum(0.05, fill * (1 - errate))
    s.requests[span] = r
    s.responses[span] = r * fill
    s.errors[span] = r * errate
    s.impressions[span] = np.maximum(0.0, r * fill - r * errate)
    s.revenue[span] = s.impressions[span] / 1000 * store.world.campaigns[target].ecpm
    s.eligible_inventory[span] = r * 1.65 * (1.0 + ivs * ramp)
    s.auction_pressure[span] = 1.0 + ps * ramp
    s.cause = cause
    s.onset_idx = n

    if cause == "TARGETING_RESTRICTION":
        store.world.campaigns[target].targeting.last_changed_at = store.now()

    bus.publish(
        "scenario.injected",
        {"scenario": scenario, "campaign_id": target,
         "campaign_name": store.world.campaigns[target].name},
    )
    return {"injected": True, "scenario": scenario, "campaign_id": target,
            "campaign_name": store.world.campaigns[target].name}


def _inject_data_outage(campaign_id: str | None) -> dict:
    target = campaign_id or _pick_healthy()
    s = store.world.series[target]
    n = store.world.idx_for(store.now())
    end = min(store.world.hours, n + 12)
    s.valid[n:end] = False
    for arr in (s.impressions, s.revenue, s.requests, s.responses, s.errors):
        arr[n:end] = 0.0
    bus.publish(
        "scenario.injected",
        {"scenario": "data_outage", "campaign_id": target,
         "campaign_name": store.world.campaigns[target].name},
    )
    return {"injected": True, "scenario": "data_outage", "campaign_id": target,
            "campaign_name": store.world.campaigns[target].name}


def _pick_healthy() -> str:
    for record in store.all_records():
        if record.health_band == "HEALTHY" and record.campaign_id != store.world.golden_id:
            if not store._open_incident_for(record.campaign_id):
                return record.campaign_id
    return next(iter(store.world.campaigns))
