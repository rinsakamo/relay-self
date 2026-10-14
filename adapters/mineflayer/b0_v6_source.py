"""S V6 bacteria-like L0 six-arm first-choice source witness, OFFLINE ONLY.

This constructs only an M0/L0 *source-shaped* decision from one caller-owned
typed Mineflayer observation. It cannot launch a World, issue an Action,
authenticate 11 physical WAIT intervals, prove paired World time, or grant V6.
No test or production runner may mistake this for a live V6 CLI admission.
"""
from __future__ import annotations

from typing import Any

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_ground_foraging import select_ground_target
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.metabolism_viability import Interoception, MetabolismConfig

V6_SOURCE_SCHEMA = "RELAYSELF_V6_B0_TWO_REGIME_G0_1"
V6_PHASES = {"LOW": 12.0, "HIGH": 20.0}
V6_ARMS = (
    "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED_HIGH",
    "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD",
)
V6_FIRST_ITEM_M0_TICK = 11
V6_HORIZON = 16
V6_MAX_MOVES = 8


class V6SourceRejected(ValueError):
    """Unsupported caller's native source or an attempt to promote G0."""


def new_v6_m0_l0_owner(
    session_id: str, *, phase: str, arm: str,
) -> B0EnergyLedger:
    """Real S ledger config, G0-only factory; no source or action authority."""
    if phase not in V6_PHASES or arm not in V6_ARMS:
        raise V6SourceRejected("unregistered V6 energy regime/control")
    if arm == "ALWAYS_SEEK":
        policy, sensor = "native_only", Interoception()
    elif arm == "ALWAYS_WAIT":
        policy, sensor = "no_ground_seek", Interoception()
    elif arm == "SENSOR_MASKED_HIGH":
        policy, sensor = "sensor_gate", Interoception(gain=0.0, bias=12.0)
    else:
        policy, sensor = "sensor_gate", Interoception()
    return B0EnergyLedger(
        session_id, config=MetabolismConfig(initial_energy=V6_PHASES[phase]),
        sensor=sensor, forage_policy=policy,
    )


def review_v6_native_wait_to_first_choice(
    wait_sources: tuple[MineflayerObservation, ...],
    item_source: MineflayerObservation, *, phase: str, arm: str,
) -> dict[str, Any]:
    """Typed 11-source L0 WAIT→M0 charge→first item choice, not physical R review.

    All source-shape checks occur before any synthetic ledger state advances.
    This cannot authenticate archived native bytes or identical elapsed World ticks.
    """
    if (
        not isinstance(wait_sources, tuple)
        or len(wait_sources) != V6_FIRST_ITEM_M0_TICK
        or not isinstance(item_source, MineflayerObservation)
        or item_source.snapshot.food != 13
        or item_source.snapshot.inventory
        or item_source.kind != "probe"
        or not item_source.request_id
        or item_source.provenance.source != "mineflayer"
    ):
        raise V6SourceRejected("V6 needs 11 original-shaped source observations")
    # The first food opportunity must contain exactly one coherent ground item.
    try:
        ground = select_ground_target(item_source)
    except ValueError as exc:
        raise V6SourceRejected("invalid first native item source") from exc
    if (
        len(item_source.snapshot.nearby_entities) != 1
        or item_source.snapshot.nearby_entities[0].distance != 2.5
    ):
        raise V6SourceRejected("first item source differs from frozen V6 opportunity")

    prior_seq = -1
    seen_requests: set[str] = set()
    for read in wait_sources:
        if (
            not isinstance(read, MineflayerObservation)
            or read.session_id != item_source.session_id
            or read.kind != "probe" or not read.request_id
            or read.request_id in seen_requests
            or read.provenance.source != "mineflayer"
            or not (prior_seq < read.seq < item_source.seq)
            or read.snapshot.nearby_entities_coverage.truncated
            or read.snapshot.nearby_entities_coverage.candidate_count
               != len(read.snapshot.nearby_entities)
            or any(e.name == "item" for e in read.snapshot.nearby_entities)
            or read.snapshot.inventory
        ):
            raise V6SourceRejected("foreign/replayed/ambiguous pre-item source")
        prior_seq = read.seq
        seen_requests.add(read.request_id)
    if item_source.request_id in seen_requests:
        raise V6SourceRejected("first food observation reuses a WAIT request")

    ledger = new_v6_m0_l0_owner(item_source.session_id, phase=phase, arm=arm)
    trace: list[dict[str, Any]] = []
    for read in wait_sources:
        choice = ledger.decide(read)
        if choice.kind != "WAIT" or choice.ground_target is not None:
            raise V6SourceRejected("source pre-item L0 not a nonissued WAIT")
        before = ledger.body.tick
        spent = ledger.step("WAIT")
        if spent.terminal_now or spent.intake != 0 or spent.expenditure != .5:
            raise V6SourceRejected("changed M0 basal/terminal dynamics")
        trace.append({
            "native_probe_seq": read.seq,
            "m0_tick_before": before,
            "m0_tick_after": ledger.body.tick,
            "l0_kind": "WAIT",
            "issued_action": False,
            "world_time_original_attested": False,
        })
    item_decision = ledger.decide(item_source)
    expected = (
        "SEEK" if (
            phase == "LOW"
            and arm in (
                "SENSOR_ON", "SHAM_ON", "ALWAYS_SEEK",
                "EQUAL_INFO_CHEAP_THRESHOLD",
            )
        ) or (phase == "HIGH" and arm == "ALWAYS_SEEK")
        else "WAIT"
    )
    if (
        ledger.body.tick != 11 or ledger.credit_count != 0
        or ledger.body.meals != 0 or item_decision.kind != expected
        or (
            item_decision.kind == "SEEK"
            and (
                item_decision.ground_target is None
                or item_decision.ground_target.entity_id != ground.entity_id
            )
        )
        or (item_decision.kind == "WAIT" and item_decision.ground_target is not None)
    ):
        raise V6SourceRejected("V6 native decision/ledger diverged from G0")
    return {
        "classification": "S_V6_TYPED_WAIT_TO_FIRST_CHOICE_SOURCE_ONLY",
        "phase": phase, "arm": arm,
        "native_session_id": item_source.session_id,
        "item_probe_seq": item_source.seq,
        "item_entity_id": ground.entity_id,
        "pre_item_waits": trace,
        "m0_tick_at_item": ledger.body.tick,
        "energy_at_item": ledger.body.energy,
        "sensor_reading_at_item": item_decision.sensor_reading,
        "l0_first_choice": item_decision.kind,
        "native_original_bytes_attested": False,
        "world_time_across_arms_matched": False,
        "world_action_issued": False,
        "native_food_pickup_attested": False,
        "m0_food_credits": 0,
        "physical_v6_runner": "NOT_IMPLEMENTED",
        "r_admission": False, "v_science_go": False,
        "physical_execution_authorized": False,
    }


def source_only_v6_first_choice(
    probe: MineflayerObservation, *, phase: str, arm: str,
) -> dict[str, Any]:
    """Pure, session-local comparator construction; no real World action."""
    if (
        phase not in V6_PHASES or arm not in V6_ARMS
        or not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe" or not probe.request_id
        or probe.snapshot.food != 13
        or probe.snapshot.inventory
    ):
        raise V6SourceRejected("source/phase/arm not a pinned V6 native opportunity")
    try:
        target = select_ground_target(probe)
    except ValueError as exc:
        raise V6SourceRejected("native one-item source not qualified") from exc
    if (
        len(probe.snapshot.nearby_entities) != 1
        or probe.snapshot.nearby_entities[0].distance != 2.5
    ):
        raise V6SourceRejected("V6 needs only the source-shaped 2.5m item")
    # Independent fresh M0 owners; no hidden truth-channel to any policy.
    ledger = new_v6_m0_l0_owner(probe.session_id, phase=phase, arm=arm)
    for _ in range(V6_FIRST_ITEM_M0_TICK):
        transition = ledger.step("WAIT")
        if transition.intake != 0 or transition.terminal_now:
            raise V6SourceRejected("unexpected synthetic M0 charge")
    decision = ledger.decide(probe)
    expected = "SEEK" if (phase == "LOW" and arm in (
        "SENSOR_ON", "SHAM_ON", "ALWAYS_SEEK", "EQUAL_INFO_CHEAP_THRESHOLD",
    )) or (phase == "HIGH" and arm == "ALWAYS_SEEK") else "WAIT"
    if (
        ledger.body.tick != 11
        or ledger.credit_count != 0 or ledger.body.meals != 0
        or decision.kind != expected
        or (decision.kind == "SEEK" and (
            decision.ground_target is None
            or decision.ground_target.entity_id != target.entity_id
        ))
        or (decision.kind == "WAIT" and decision.ground_target is not None)
    ):
        raise V6SourceRejected("existing S owner L0 policy disagrees with V6 G0")
    return {
        "classification": "S_V6_B0_SOURCE_ONLY_FIRST_CHOICE_NOT_WORLD",
        "schema": V6_SOURCE_SCHEMA, "phase": phase, "arm": arm,
        "first_opportunity_m0_tick": ledger.body.tick,
        "true_m0_energy": ledger.body.energy,
        "sensor_reading": decision.sensor_reading,
        "native_session_id": probe.session_id, "native_probe_seq": probe.seq,
        "ground_item_entity_id": target.entity_id,
        "l0_kind": decision.kind,
        "source_world_food": probe.snapshot.food,
        "intake_credit_count": ledger.credit_count,
        "issued_action": False,
        "native_original_bytes_attested": False,
        "eleven_wait_world_intervals_attested": False,
        "matched_native_world_time_attested": False,
        "equal_information_cheap_advantage": "NONE_EXPECTED",
        "physical_v6_six_arm_runner": "NOT_IMPLEMENTED",
        "external_food_command_time_attested": False,
        "v_science_go": False, "physical_execution_authorized": False,
    }
