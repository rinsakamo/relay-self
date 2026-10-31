"""SelfBody #632 consumer seam for S50 #645 sampled-motion diagnostics.

Read-only, optional, one existing SelfBodyView + separate S50 sidecar.
No new native Present, physical truth, L0/L1/L2 policy or Action authority.
The supplied S50 dict is a previously reviewed producer *claim*; it is
not independently attested by this consumer. The owner must supply its
original, already-interpreted S16 OUTCOME to join the same Action.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import SelfBodyView

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MAX_TICKS = 8
_SOURCE_SCHEMA = "S50_SELFBODY_MOTION_DIAGNOSTIC_V0"
_FLAGS_OFF_CEILING = "DIAGNOSTIC_ONLY_NOT_NATIVE_PRESENT"


class SelfBodyS50MotionRejected(ValueError):
    """Unjoined, foreign, malformed, or over-promoted source sidecar."""


class SampledBodyMotion(str, Enum):
    """Observed callback delta only, *never* verified full-tick physical state."""

    SAMPLED_POSITION_CHANGED = "sampled_position_changed"
    SAMPLED_ZERO_DELTA = "sampled_zero_delta"


@dataclass(frozen=True, slots=True)
class SelfBodyMotionReading:
    world_tick: int
    displacement_m: float
    last_reported_input_active: bool
    sampled_motion: SampledBodyMotion
    paper_source_sha256: str
    provenance_scope: str = "S50_PAPER_CALLBACK_SAMPLE_NOT_NATIVE_PRESENT"
    physical_stability_attested: bool = False
    p1_wait_granted: bool = False
    goal_admitted: bool = False


@dataclass(frozen=True, slots=True)
class SelfBodyS50MotionCompanion:
    """Parallel cognition readout beside original SelfBodyView, not *inside* it.

    Carries source labels, not a new owner truth or an Action result.
    Every value remains a sampled, fallible physical diagnostic.
    """

    self_body: SelfBodyView
    action_id: str
    paper_world_uuid: str
    paper_source_sha256: str
    client_source_sha256: str
    ticks: tuple[SelfBodyMotionReading, ...]
    client_control_effects: tuple[str, ...]
    client_player_input_write_returns: int
    client_position_write_returns: int
    paper_player_input_callbacks: int
    source_classification: str = "SELF_BODY_S50_SUPPLEMENT_ONLY"
    world_client_clock_alignment: str = "NOT_ATTESTED"
    effective_clear_world_tick: str = "NOT_ATTESTED"
    native_present_minted: bool = False
    physically_stopped_attested: bool = False
    p1_wait_granted: bool = False
    l10_pairs_admitted: int = 0
    s10_updates_admitted: int = 0
    s11_grants_admitted: int = 0
    science_run: bool = False

    def sampled_at(self, world_tick: int) -> SelfBodyMotionReading | None:
        """Explicit Paper fullTime query, not native epoch/tick synchronization."""
        if type(world_tick) is not int or world_tick < 0:
            raise SelfBodyS50MotionRejected("Paper world_tick must be a natural int")
        return next((row for row in self.ticks if row.world_tick == world_tick), None)

    def cognitive_summary(self) -> dict[str, object]:
        """Bounded read-only diagnostic, NO policy/action selection or STOP grant."""
        return {
            "classification": self.source_classification,
            "session_id": self.self_body.session_id,
            "epoch_id": self.self_body.epoch_id,
            "world": self.paper_world_uuid,
            "paper_source_sha256": self.paper_source_sha256,
            "ticks_sampled": len(self.ticks),
            "changed_with_last_reported_input_off": tuple(
                row.world_tick for row in self.ticks
                if row.sampled_motion is SampledBodyMotion.SAMPLED_POSITION_CHANGED
                and not row.last_reported_input_active
            ),
            "last_reported_input_is_full_tick_input": False,
            "physically_stopped_attested": False,
            "effective_clear_world_tick": "NOT_ATTESTED",
            "world_client_clock_alignment": "NOT_ATTESTED",
            "goal_admitted": False,
            "p1_wait_granted": False,
            "native_present_minted": False,
            "learning_updates": 0,
            "action_issued": False,
            "model_calls": 0,
        }


def _required(row: Mapping[str, object], key: str, cls: type) -> object:
    value = row.get(key)
    if type(value) is not cls:
        raise SelfBodyS50MotionRejected(f"malformed S50 source field: {key}")
    return value


def _same_ceiling(source: Mapping[str, object]) -> None:
    limits = {
        "schema": _SOURCE_SCHEMA,
        "provenance_ceiling": _FLAGS_OFF_CEILING,
        "cross_clock_alignment": "NOT_ATTESTED",
        "effective_s15_clear_world_tick": "NOT_ATTESTED",
        "full_tick_input_coverage": False,
        "physically_stopped_attested": False,
        "goal_admitted": False,
        "p1_wait_ticks_admitted": 0,
        "l10_pairs_admitted": 0,
        "s10_updates_admitted": 0,
        "s11_grants_admitted": 0,
    }
    if any(type(source.get(key)) is not type(expected) or
           source.get(key) != expected for key, expected in limits.items()):
        raise SelfBodyS50MotionRejected("S50 source exceeds diagnostic authority")


def compose_self_body_s50_motion_companion(
    self_body: SelfBodyView, source: Mapping[str, object],
) -> SelfBodyS50MotionCompanion:
    """Join only to same native S16 Action in an already-built SelfBody view.

    Neither a Paper marker nor an S15 clear ACK qualifies S16 alone.
    The S50 producer's bytes/source check is an upstream responsibility.
    This adapter never calls the S49 issuer or changes the existing view.
    """
    if not isinstance(self_body, SelfBodyView) or not isinstance(source, dict):
        raise SelfBodyS50MotionRejected("typed existing SelfBody and S50 source required")
    _same_ceiling(source)
    outcome = self_body.outcome
    if (
        outcome is None or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
        or outcome.reason_code != "observed_execution"
        or outcome.source_status != "executed"
        or outcome.session_id != self_body.session_id
    ):
        raise SelfBodyS50MotionRejected("missing exact original S16 OUTCOME")
    session = _required(source, "session_id", str)
    action = _required(source, "action_id", str)
    marker = _required(source, "marker_id", str)
    world = _required(source, "paper_world_uuid", str)
    subject = _required(source, "subject_uuid", str)
    if (
        not 0 < len(session) <= 128
        or not 0 < len(action) <= 128
        or session != self_body.session_id
        or action != outcome.action_id
        or marker != f"{action}-{session}"
        or not 0 < len(world) <= 128
        or not 0 < len(subject) <= 128
    ):
        raise SelfBodyS50MotionRejected("S50 source foreign session/action/marker/World")
    if (
        self_body.observation is None
        or self_body.observation.action_id != action
        or self_body.observation.consequence_provenance != outcome.world_provenance
    ):
        raise SelfBodyS50MotionRejected(
            "original action-associated native Present not admitted in SelfBody"
        )
    paper_sha = _required(source, "paper_original_sha256", str)
    client_sha = _required(source, "client_original_sha256", str)
    if not _SHA.fullmatch(paper_sha) or not _SHA.fullmatch(client_sha):
        raise SelfBodyS50MotionRejected("source must identify bounded original SHA256")
    raw_ticks = _required(source, "paper_samples", list)
    raw_effects = _required(source, "client_effects", list)
    if len(raw_ticks) != _MAX_TICKS or not 1 <= len(raw_effects) <= 8:
        raise SelfBodyS50MotionRejected("invalid S50 source sample count")
    ticks = []
    for i, raw in enumerate(raw_ticks):
        if not isinstance(raw, dict):
            raise SelfBodyS50MotionRejected("Paper tick row must be a mapping")
        tick = _required(raw, "world_tick", int)
        delta = raw.get("displacement_m")
        active = _required(raw, "last_reported_input_active", bool)
        if (
            tick < 0 or (ticks and tick != ticks[-1].world_tick + 1)
            or type(delta) not in (int, float) or not math.isfinite(delta)
            or delta < 0 or delta > 128.0
            or raw.get("source_scope") != "PAPER_CALLBACK_SAMPLE_ONLY"
        ):
            raise SelfBodyS50MotionRejected("invalid sampled physical delta/clock")
        ticks.append(SelfBodyMotionReading(
            world_tick=tick, displacement_m=float(delta),
            last_reported_input_active=active,
            sampled_motion=(
                SampledBodyMotion.SAMPLED_POSITION_CHANGED
                if delta > 0 else SampledBodyMotion.SAMPLED_ZERO_DELTA
            ),
            paper_source_sha256=paper_sha,
        ))
    if ticks[0].world_tick < 1:
        raise SelfBodyS50MotionRejected("Paper first tick not bound")
    effects = []
    prev = -1
    for item in raw_effects:
        if not isinstance(item, dict):
            raise SelfBodyS50MotionRejected("client effect must be a mapping")
        kind = _required(item, "effect", str)
        index = _required(item, "node_record_index", int)
        active = _required(item, "local_controls_active", bool)
        if (
            kind not in {"set_control", "clear_controls", "shutdown_clear_controls"}
            or index <= prev or item.get("source_scope") !=
            "CLIENT_LOCAL_CONTROL_SNAPSHOT_ONLY"
            or (kind in {"clear_controls", "shutdown_clear_controls"} and active)
        ):
            raise SelfBodyS50MotionRejected("client local control sample unqualified")
        effects.append(kind)
        prev = index
    if "clear_controls" not in effects:
        raise SelfBodyS50MotionRejected("missing original local clear sample")
    off_ticks = _required(source, "observed_motion_while_reported_input_off_ticks", list)
    actual_off = [row.world_tick for row in ticks if
                  row.sampled_motion is SampledBodyMotion.SAMPLED_POSITION_CHANGED
                  and not row.last_reported_input_active]
    if off_ticks != actual_off:
        raise SelfBodyS50MotionRejected("S50 motion/input diagnostic changed")
    counts = []
    for key in (
        "client_player_input_write_returns",
        "client_position_write_returns",
        "paper_player_input_callbacks",
    ):
        v = _required(source, key, int)
        if not 0 <= v <= 8192:
            raise SelfBodyS50MotionRejected("unbounded S50 packet count")
        counts.append(v)
    diagnostic = _required(source, "client_packet_diagnostic", str)
    if diagnostic not in {
        "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH",
        "PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT",
        "BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN",
    }:
        raise SelfBodyS50MotionRejected("invalid packet diagnostic classification")
    if (
        (counts[0] == 0 and diagnostic != "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH")
        or (counts[0] > 0 and counts[2] == 0 and
            diagnostic != "PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT")
        or (counts[0] > 0 and counts[2] > 0 and
            diagnostic != "BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN")
    ):
        raise SelfBodyS50MotionRejected("client/Paper diagnostic counter mismatch")
    return SelfBodyS50MotionCompanion(
        self_body=self_body,
        action_id=action, paper_world_uuid=world,
        paper_source_sha256=paper_sha, client_source_sha256=client_sha,
        ticks=tuple(ticks), client_control_effects=tuple(effects),
        client_player_input_write_returns=counts[0],
        client_position_write_returns=counts[1],
        paper_player_input_callbacks=counts[2],
    )
