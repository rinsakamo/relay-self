"""M #616: B0-owner-compatible resource cognition view, read-only.

Consume the *existing* S #634 B0CognitionViews after the B0 L0 decision.
This uses M0 MetabolismConfig one-tick costs, NEVER M0.1 distance pricing.
No additional source read, true-E access, policy, motor, food credit or owner.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_viability import Interoception, MetabolismConfig

B0Affordability = Literal[
    "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT", "MODEL_AMBIGUOUS", "UNKNOWN"
]


@dataclass(frozen=True, slots=True)
class B0TickResourceFact:
    activity: Literal["WAIT", "MOVE"]
    modeled_energy_cost: float
    affordability: B0Affordability
    reason: str


@dataclass(frozen=True, slots=True)
class B0CognitiveResourceView:
    """A bound one-epoch simulation, never a next Action request."""

    self_id: str
    session_id: str
    epoch_id: str
    native_seq: int
    owner_tick: int
    original_l0_kind: str
    native_source_ref: str
    owner_sensor_ref: str
    energy_lower: float | None
    energy_upper: float | None
    facts: tuple[B0TickResourceFact, ...]
    action_authority: bool = False
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    source_scope: str = "B0_M0_OFFLINE_SIMULATION_NOT_S49_OR_WORLD_ATTESTED"


def _bounds(
    reading: float,
    sensor: Interoception,
    capacity: float,
    noise_bound: float | None,
) -> tuple[float, float] | None:
    # No artificial confidence for unknown, unbounded or blind sensors.
    if noise_bound is None or sensor.gain <= 0:
        return None
    width = sensor.quantum / 2.0 + noise_bound
    if not math.isfinite(width):
        return None
    lo = (reading - sensor.bias - width) / sensor.gain
    hi = (reading - sensor.bias + width) / sensor.gain
    if not math.isfinite(lo) or not math.isfinite(hi):
        return None
    if hi < 0 or lo > capacity:
        return None
    return (
        max(0.0, math.nextafter(lo, -math.inf)),
        min(capacity, math.nextafter(hi, math.inf)),
    )


def _fact(
    activity: Literal["WAIT", "MOVE"], cost: float,
    bounds: tuple[float, float] | None,
) -> B0TickResourceFact:
    if bounds is None:
        status: B0Affordability = "UNKNOWN"
        reason = "UNKNOWN_B0_SENSOR_RANGE"
    elif bounds[0] > cost:
        status = "MODEL_AFFORDABLE"
        reason = "CONDITIONAL_B0_ONE_TICK"
    elif bounds[1] <= cost:
        status = "MODEL_INSUFFICIENT"
        reason = "CONDITIONAL_B0_ONE_TICK"
    else:
        status = "MODEL_AMBIGUOUS"
        reason = "B0_SENSOR_INTERVAL_OVERLAPS_TERMINAL_COST"
    return B0TickResourceFact(activity, cost, status, reason)


def read_b0_resource_context(
    views: object,
    *,
    config: MetabolismConfig,
    sensor: Interoception,
    noise_bound: float | None = None,
) -> B0CognitiveResourceView:
    """Read existing B0 decision's one source-bound SelfBody/World pair.

    The S owner supplies the actual B0 model profile and sensor calibration;
    this module cannot independently authenticate the calibration or native
    probe. Unlike M0.1, B0 MOVE cost is per *simulated action tick*, not per
    measured block. No EAT candidate is evaluated: only an original S51
    verified EAT outcome can create food credit.
    """
    if not isinstance(config, MetabolismConfig) or not isinstance(sensor, Interoception):
        raise ValueError("typed existing B0 energy model and sensor required")
    if noise_bound is not None and (
        type(noise_bound) not in (float, int)
        or not math.isfinite(noise_bound)
        or noise_bound < 0
    ):
        raise ValueError("nonnegative bounded noise or UNKNOWN required")
    if (
        getattr(views, "source_scope", None)
        != "B0_M0_OWNER_LOCAL_DEV_NOT_PHYSICAL_ATTESTATION"
        or type(getattr(views, "sensor_tick", None)) is not int
        or views.sensor_tick < 0
        or getattr(views, "l0_kind", None) not in ("WAIT", "SEEK", "EAT")
    ):
        raise ValueError("existing B0 cognition producer required")
    body = getattr(views, "body", None)
    world = getattr(views, "world", None)
    if (
        body is None
        or world is None
        or getattr(world, "self_body", None) is not body
        or not isinstance(getattr(body, "self_id", None), str)
        or not body.self_id
        or not isinstance(getattr(body, "session_id", None), str)
        or not body.session_id
        or not isinstance(getattr(body, "epoch_id", None), str)
        or not body.epoch_id
    ):
        raise ValueError("original joined SelfWorld and SelfBody required")
    obs = getattr(body, "observation", None)
    wobs = getattr(world, "observation", None)
    if (
        obs is None or wobs is None
        or obs.session_id != body.session_id
        or wobs.session_id != body.session_id
        or obs.native_seq != wobs.native_seq
        or obs.request_id != wobs.request_id
        or obs.source_provenance != wobs.provenance
        or obs.source_ref != (
            f"native-probe:{body.session_id}:{obs.native_seq}:{obs.request_id}"
        )
    ):
        raise ValueError("foreign or unjoined native B0 observation")
    sensors = getattr(body, "interoceptions", ())
    if not isinstance(sensors, tuple):
        raise ValueError("source-bound sensor tuple required")
    item = tuple(
        s for s in sensors
        if getattr(getattr(s, "field", None), "key", None) == "m0_energy_sensor"
    )
    if len(item) != 1:
        raise ValueError("exactly one B0 owner energy sensor required")
    item = item[0]
    reading = body.sensed("m0_energy_sensor")
    owner_ref = (
        f"{body.session_id}:{views.sensor_tick}:{obs.native_seq}:{obs.request_id}"
    )
    if (
        getattr(getattr(reading, "origin", None), "value", None) != "interoception"
        or reading.key != "m0_energy_sensor"
        or type(reading.value) not in (float, int)
        or not math.isfinite(reading.value)
        or item.field.value != reading.value
        or item.session_id != body.session_id
        or item.native_seq != obs.native_seq
        or item.request_id != obs.request_id
        or item.owner_tick != views.sensor_tick
        or item.native_provenance != obs.source_provenance
        or getattr(item.owner_provenance, "source", None)
        != "b0-m0-owner-local-sensor"
        or getattr(item.owner_provenance, "reference", None) != owner_ref
        or reading.source_refs != (
            obs.source_ref,
            f"body-sensor:{body.session_id}:{obs.native_seq}:"
            f"{views.sensor_tick}:{obs.request_id}",
        )
        or reading.provenance
        != (obs.source_provenance, item.owner_provenance)
    ):
        raise ValueError("B0 source/tick/sensor binding mismatch")
    bounds = _bounds(reading.value, sensor, config.capacity, noise_bound)
    return B0CognitiveResourceView(
        body.self_id, body.session_id, body.epoch_id,
        obs.native_seq, views.sensor_tick, views.l0_kind,
        obs.source_ref, owner_ref,
        bounds[0] if bounds is not None else None,
        bounds[1] if bounds is not None else None,
        (
            _fact("WAIT", config.basal_cost, bounds),
            _fact("MOVE", config.basal_cost + config.move_cost, bounds),
        ),
    )
