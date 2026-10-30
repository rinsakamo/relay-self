"""M #616: read-only SelfBody -> M1/L2 resource context, no owner promotion.

The current product SelfBody B0 'm0_energy_sensor' is *NOT* a calibrated
M0.1 sensor and may not be used to judge M0.1 travel costs.
A future M0.1 product owner must explicitly supply its matching projected
reading and matching BodyInteroception; no live producer is installed here.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal

from experiments.metabolism_m01_minecraft import M01Profile, M01State
from experiments.metabolism_resource_projection import SelfBodyResourceCosts
from experiments.metabolism_route_bounds import (
    RouteComparison,
    RouteCostRange,
    SensedRouteAffordability,
    compare_route_ranges,
)
from experiments.metabolism_sensed_viability import assess_sensed_costs
from experiments.metabolism_viability import (
    BodyState,
    Interoception,
    observe_energy,
)

M01_SENSOR_KEY = "m01_energy_sensor"
B0_SENSOR_KEY = "m0_energy_sensor"


@dataclass(frozen=True)
class M01OwnerSensorHandoff:
    """Owner-local calibrated sensor result, with no physical true Energy."""

    session_id: str
    world_tick: int
    native_seq: int
    request_id: str
    native_source_ref: str
    owner_source_ref: str
    profile_sha256: str
    reading: float
    source_scope: str = "M01_PRODUCER_LOCAL_NOT_NATIVE_ATTESTED"


@dataclass(frozen=True)
class CognitiveResourceContext:
    """Immutable per-epoch information; L/S retains all choice authority."""

    self_id: str
    session_id: str
    epoch_id: str
    native_seq: int
    owner_world_tick: int | None
    sensor_model: Literal["M01_OWNER_LOCAL", "UNBOUND"]
    results: tuple[SensedRouteAffordability, ...]
    reason: str
    action_authority: bool = False
    learning_updates: int = 0
    habit_grants: int = 0
    source_scope: str = "M_OFFLINE_COGNITIVE_INPUT_NO_S49_AUTHORITY"


def _profile_sha(profile: M01Profile) -> str:
    if not isinstance(profile, M01Profile):
        raise ValueError("typed M0.1 profile required")
    payload = json.dumps(asdict(profile), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def export_m01_owner_sensor(
    profile: M01Profile,
    state: M01State,
    sensor: Interoception,
    *,
    native_seq: int,
    request_id: str,
) -> M01OwnerSensorHandoff:
    """An M0.1 owner-side *offline* readout; never export true E.

    The S owner must correlate the original native source and create the
    BodyInteroception. These self-consistent local refs are not attestation.
    """
    if (
        not isinstance(state, M01State)
        or not isinstance(sensor, Interoception)
        or state.profile_id != profile.profile_id
        or not isinstance(state.session_id, str)
        or not state.session_id
        or type(state.world_tick) is not int
        or state.world_tick < 0
        or not math.isfinite(state.energy)
        or not 0 < state.energy <= profile.capacity
        or state.terminal
        or type(native_seq) is not int
        or native_seq < 0
        or not isinstance(request_id, str)
        or not request_id
    ):
        raise ValueError("live same-profile M0.1 owner and native identity required")
    reading = observe_energy(BodyState(state.energy, state.world_tick), sensor)
    native_ref = f"native-probe:{state.session_id}:{native_seq}:{request_id}"
    owner_ref = (
        f"{state.session_id}:{state.world_tick}:{native_seq}:{request_id}"
    )
    return M01OwnerSensorHandoff(
        state.session_id,
        state.world_tick,
        native_seq,
        request_id,
        native_ref,
        owner_ref,
        _profile_sha(profile),
        reading.reading,
    )


def _validate_body(body: object) -> tuple[object, object]:
    """Check the existing SelfBodyView field names without importing S owner.

    Structural checks are not source authentication; S can optionally import
    this M module on its own branch and retain its typed validation.
    """
    observation = getattr(body, "observation", None)
    if (
        not isinstance(getattr(body, "session_id", None), str)
        or not body.session_id
        or not isinstance(getattr(body, "epoch_id", None), str)
        or not body.epoch_id
        or not isinstance(getattr(body, "self_id", None), str)
        or not body.self_id
        or observation is None
        or observation.session_id != body.session_id
        or type(observation.native_seq) is not int
        or observation.native_seq < 0
        or not isinstance(observation.request_id, str)
        or not observation.request_id
        or observation.source_ref != (
            f"native-probe:{body.session_id}:{observation.native_seq}:"
            f"{observation.request_id}"
        )
        or not isinstance(getattr(body, "interoceptions", None), tuple)
        or not callable(getattr(body, "sensed", None))
    ):
        raise ValueError("valid S SelfBody Present/epoch shape required")
    return observation, body.sensed(M01_SENSOR_KEY)


def _unknown(
    body: object,
    observation: object,
    ranges: tuple[RouteCostRange, ...],
    reason: str,
) -> CognitiveResourceContext:
    result = tuple(
        SensedRouteAffordability(
            r.label, r.destination, "UNKNOWN", None, None, reason
        )
        for r in ranges
    )
    return CognitiveResourceContext(
        body.self_id, body.session_id, body.epoch_id,
        observation.native_seq, None, "UNBOUND", result, reason,
    )


def from_selfbody_to_cognition(
    body: object,
    *,
    profile: M01Profile,
    sensor: Interoception,
    route_ranges: tuple[RouteCostRange, ...],
    handoff: M01OwnerSensorHandoff | None = None,
    noise_bound: float | None = None,
) -> CognitiveResourceContext:
    """Return L1/L2-readable facts, NEVER change the existing S decision.

    B0 'm0_energy_sensor' on existing SelfBody is deliberately insufficient:
    its B0 Energy owner/calibration is *not* the M0.1 state of route quotes.
    Only a separately joined, exact-profile, owner-local M0.1 sensor
    projection can produce model-conditional statuses. S must authorize
    both native source and the BodyInteroception before adopting this hook.
    """
    if not isinstance(profile, M01Profile) or not isinstance(sensor, Interoception):
        raise ValueError("typed M profile/sensor required")
    obs, sensed = _validate_body(body)
    if not isinstance(route_ranges, tuple) or any(
        not isinstance(r, RouteCostRange)
        or r.session_id != body.session_id
        or r.owner_world_tick < 0
        for r in route_ranges
    ):
        raise ValueError("typed session-matched M candidate ranges required")
    if len({r.label for r in route_ranges}) != len(route_ranges):
        raise ValueError("duplicate cognitive candidate labels")
    if handoff is None:
        # Existing B0 has a different physical model and cannot bind M0.1.
        return _unknown(body, obs, route_ranges, "M01_SENSOR_NOT_BOUND_B0_IS_DIFFERENT_MODEL")
    if (
        not isinstance(handoff, M01OwnerSensorHandoff)
        or handoff.source_scope != "M01_PRODUCER_LOCAL_NOT_NATIVE_ATTESTED"
        or handoff.profile_sha256 != _profile_sha(profile)
        or handoff.session_id != body.session_id
        or handoff.native_seq != obs.native_seq
        or handoff.request_id != obs.request_id
        or handoff.native_source_ref != obs.source_ref
        or type(handoff.world_tick) is not int
        or handoff.world_tick < 0
        or not math.isfinite(handoff.reading)
        or handoff.owner_source_ref != (
            f"{body.session_id}:{handoff.world_tick}:{obs.native_seq}:"
            f"{obs.request_id}"
        )
        or any(r.owner_world_tick != handoff.world_tick for r in route_ranges)
    ):
        raise ValueError("unbound, stale or mismatched M0.1 owner readout")
    sensor_item = tuple(
        item for item in body.interoceptions
        if getattr(getattr(item, "field", None), "key", None) == M01_SENSOR_KEY
    )
    if len(sensor_item) != 1:
        raise ValueError("missing or duplicate M0.1 SelfBody interoception")
    item = sensor_item[0]
    origin = getattr(getattr(sensed, "origin", None), "value", None)
    native_source = getattr(item, "native_provenance", None)
    owner_source = getattr(item, "owner_provenance", None)
    if (
        origin != "interoception"
        or sensed.key != M01_SENSOR_KEY
        or type(sensed.value) not in (float, int)
        or not math.isfinite(sensed.value)
        or sensed.value != handoff.reading
        or item.session_id != body.session_id
        or item.native_seq != obs.native_seq
        or item.request_id != obs.request_id
        or item.owner_tick != handoff.world_tick
        or item.field.value != sensed.value
        or native_source != obs.source_provenance
        or getattr(owner_source, "source", None) != "m01-owner-local-sensor"
        or getattr(owner_source, "reference", None) != handoff.owner_source_ref
        or sensed.source_refs[0] != obs.source_ref
        or sensed.provenance != (native_source, owner_source)
    ):
        raise ValueError("SelfBody origin, owner tick or source lineage mismatch")
    public = SelfBodyResourceCosts(
        body.session_id, handoff.world_tick, sensed.value, ()
    )
    sensed_model = assess_sensed_costs(
        profile, public, sensor, noise_bound=noise_bound
    )
    compared: RouteComparison = compare_route_ranges(sensed_model, route_ranges)
    return CognitiveResourceContext(
        body.self_id, body.session_id, body.epoch_id,
        obs.native_seq, handoff.world_tick, "M01_OWNER_LOCAL",
        compared.results, "MODEL_CONDITIONAL_OWNER_LOCAL_NOT_WORLD_ATTESTED",
    )
