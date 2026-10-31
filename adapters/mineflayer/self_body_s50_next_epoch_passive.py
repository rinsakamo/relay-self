"""SelfBody #632 DEV: prior S50 motion -> next ORIGINAL S49 probe epoch.

This is an optional, one-shot read-only product observer for the *existing*
S49 `live_probe` callback (called before original L0 decision). It does not
request a probe, issue an Action, change S49 L0 choice, write P1/M/L8/S10,
or promote the preceding S50 Paper samples to native Present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_body_s50_motion_companion import (
    SelfBodyS50MotionCompanion,
)
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.self_body import SelfBodyView, compose_self_body_view
from relay_self.self_world import SelfWorldView, compose_self_world_view

_REQUEST = re.compile(r"s49-actual:([^:]+):event-([0-9]+)\Z")
_ACTION = re.compile(r"s49-native-move-([0-9]+)\Z")


class SelfBodyS50NextEpochRejected(ValueError):
    """Stale/foreign source, replay, or missing original next native probe."""


@dataclass(frozen=True, slots=True)
class SelfBodyS50NextEpochReadout:
    """One NEW native Present and old S50 diagnostic, never same-tick evidence."""

    current_body: SelfBodyView
    current_world: SelfWorldView
    previous_motion: SelfBodyS50MotionCompanion
    source_scope: str = "NEXT_ORIGINAL_S49_PROBE_READ_ONLY"
    separate_paper_and_node_clocks: bool = True
    original_l0_decision_modified: bool = False
    native_probes_added: int = 0
    action_issuers_added: int = 0
    p1_wait_granted: int = 0
    learning_updates: int = 0

    def read_previous_motion(self) -> dict[str, object]:
        """An explicit read during the later epoch, not the next L0 policy."""
        previous = self.previous_motion.cognitive_summary()
        return {
            "classification": "S50_PRIOR_ACTION_DIAGNOSTIC_READ_IN_NEXT_NATIVE_EPOCH",
            "session_id": self.current_body.session_id,
            "current_epoch_id": self.current_body.epoch_id,
            "current_native_source_ref": self.current_body.observation.source_ref,
            "current_world_source_ref": self.current_world.observation.source_ref,
            "previous_action_id": self.previous_motion.action_id,
            "previous_motion_changed_with_input_off": previous[
                "changed_with_last_reported_input_off"
            ],
            "prior_source_sha256": self.previous_motion.paper_source_sha256,
            "current_position_x": self.current_body.observed("position_x").value,
            "prior_paper_samples_not_current_native_present": True,
            "paper_node_world_clock_alignment": "NOT_ATTESTED",
            "prior_effective_s15_clear_tick": "NOT_ATTESTED",
            "full_tick_input_idle": "NOT_ATTESTED",
            "physical_stability": "UNPROVEN",
            "goal_admitted": False,
            "p1_wait_granted": 0,
            "learning_updates": 0,
            "s10_updates": 0,
            "s11_grants": 0,
            "new_actions": 0,
            "new_model_calls": 0,
        }


class SelfBodyS50NextEpochLease:
    """One original after-S16 companion -> ONE later S49 native probe readout.

    Its `observe_existing_s49_probe` is safe as S49's `live_probe`: even
    malformed inputs return without raising into L0, and revoke this lease.
    """

    def __init__(self, previous: SelfBodyS50MotionCompanion) -> None:
        if not isinstance(previous, SelfBodyS50MotionCompanion):
            raise SelfBodyS50NextEpochRejected("previous typed S50 companion required")
        old = previous.self_body
        observation = old.observation
        outcome = old.outcome
        if (
            observation is None or outcome is None
            or observation.action_id != previous.action_id
            or observation.consequence_provenance != outcome.world_provenance
            or observation.session_id != old.session_id
            or old.self_id is None
            or old.epoch_id == ""
            or previous.effective_clear_world_tick != "NOT_ATTESTED"
            or previous.native_present_minted
            or previous.physically_stopped_attested
            or previous.p1_wait_granted
        ):
            raise SelfBodyS50NextEpochRejected("unqualified prior Action-native source")
        self._previous: SelfBodyS50MotionCompanion | None = previous
        self._last_native_seq = observation.native_seq
        self._last_source_ref = observation.source_ref
        self._session_id = old.session_id
        self._self_id = old.self_id
        self._old_epoch = old.epoch_id
        action = _ACTION.fullmatch(previous.action_id)
        self._last_action_event = int(action.group(1)) if action else None
        self._used = False
        self._closed = False
        self._status = "WAITING_FOR_NEXT_ORIGINAL_S49_PROBE"
        self._errors: tuple[str, ...] = ()
        self._readout: SelfBodyS50NextEpochReadout | None = None
        self._read_count = 0

    async def observe_existing_s49_probe(self, reading: MineflayerObservation) -> None:
        """No await/new I/O; called only by already-existing S49 live_probe hook."""
        if self._used or self._closed:
            self._revoke("DUPLICATE_OR_EXPIRED_NEXT_PROBE")
            return
        self._used = True
        try:
            if not isinstance(reading, MineflayerObservation) or reading.kind != "probe":
                raise SelfBodyS50NextEpochRejected("original typed S49 probe required")
            match = _REQUEST.fullmatch(reading.request_id or "")
            if (
                match is None
                or match.group(1) != self._session_id
                or reading.session_id != self._session_id
                or reading.seq <= self._last_native_seq
                or (
                    self._last_action_event is not None
                    and int(match.group(2)) <= self._last_action_event
                )
            ):
                raise SelfBodyS50NextEpochRejected(
                    "stale/foreign/replayed S49 decision event after Action"
                )
            previous = self._previous
            assert previous is not None
            present = project_mineflayer_present(reading)
            body_present = project_body_present(present)
            current_epoch = f"s49-next-event-{match.group(2)}-native-{reading.seq}"
            if current_epoch == self._old_epoch:
                raise SelfBodyS50NextEpochRejected("epoch was not advanced")
            next_body = compose_self_body_view(
                self_id=self._self_id,
                session_id=self._session_id,
                epoch_id=current_epoch,
                observation=body_present,
                minimum_native_seq=self._last_native_seq + 1,
                seen_observation_refs=(self._last_source_ref,),
            )
            next_world = compose_self_world_view(
                self_id=self._self_id,
                session_id=self._session_id,
                epoch_id=current_epoch,
                self_body=next_body,
                observation=project_self_world_present(
                    present, observer_id=self._self_id
                ),
                minimum_native_seq=self._last_native_seq + 1,
            )
            if (
                next_world.self_body is not next_body
                or next_body.observation is not body_present
                or next_world.observation.native_seq != body_present.native_seq
                or next_world.observation.provenance != body_present.source_provenance
                or next_world.observation.request_id != body_present.request_id
            ):
                raise SelfBodyS50NextEpochRejected("Body/World original-source mismatch")
            self._readout = SelfBodyS50NextEpochReadout(
                current_body=next_body,
                current_world=next_world,
                previous_motion=previous,
            )
            # Explicitly dereference the prior diagnostic in the NEW epoch.
            self._readout.read_previous_motion()
            self._read_count = 1
            self._status = "NEXT_ORIGINAL_NATIVE_EPOCH_READ_ONCE"
        except Exception as exc:
            self._revoke(type(exc).__name__)
        finally:
            # Previous receipt must not live beyond this next native epoch.
            self._previous = None

    def take_readout_once(self) -> SelfBodyS50NextEpochReadout:
        if (
            self._closed or self._readout is None
            or self._status != "NEXT_ORIGINAL_NATIVE_EPOCH_READ_ONCE"
        ):
            raise SelfBodyS50NextEpochRejected("no next native epoch readout")
        readout = self._readout
        self._readout = None
        self._closed = True
        self._status = "NEXT_EPOCH_READOUT_CONSUMED"
        return readout

    def close(self) -> None:
        self._previous = None
        self._readout = None
        self._closed = True
        if self._status == "WAITING_FOR_NEXT_ORIGINAL_S49_PROBE":
            self._status = "EXPIRED_WITHOUT_NEXT_NATIVE_EPOCH"

    def _revoke(self, reason: str) -> None:
        self._previous = None
        self._readout = None
        self._closed = True
        self._status = "REVOKED_NEXT_NATIVE_EPOCH_SOURCE"
        self._errors = (*self._errors, reason)

    def status(self) -> dict[str, object]:
        return {
            "status": self._status,
            "next_native_source_read_count": self._read_count,
            "source_errors": self._errors,
            "readout_available": self._readout is not None and not self._closed,
            "extra_native_probes": 0,
            "new_action_issuers": 0,
            "new_packet_writes": 0,
            "new_model_calls": 0,
            "memory_writes": 0,
            "p1_wait_admitted": 0,
            "l10_pairs_admitted": 0,
            "goal_admitted": False,
        }
