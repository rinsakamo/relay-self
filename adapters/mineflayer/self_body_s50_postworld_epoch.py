"""SelfBody DEV: one internal cognition epoch AFTER a closed World session.

Prior actual S49/S16/native Present and S50 Paper sampled motion remain
readable as *past evidence*; current native Body/World state is UNKNOWN.
No live Mineflayer source, extra probe, Action, learning, P1, or model.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.self_body_s50_motion_companion import (
    SelfBodyS50MotionCompanion,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import BodyOrigin, SelfBodyView, compose_self_body_view
from relay_self.self_world import SelfWorldView, compose_self_world_view


class PostWorldInternalEpochRejected(ValueError):
    """No legitimate prior closed-Action source or post-shutdown boundary."""


@dataclass(frozen=True, slots=True)
class PostWorldInternalEpochReadout:
    """Original owner-projected new internal epoch; NOT a fresh native epoch."""

    internal_body: SelfBodyView
    internal_world: SelfWorldView
    previous_motion: SelfBodyS50MotionCompanion
    prior_native_source_ref: str
    classification: str = "POST_WORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_ONLY"
    new_native_present: bool = False
    native_probe_count: int = 0
    new_actions: int = 0
    model_calls: int = 0
    p1_wait_grants: int = 0
    learning_updates: int = 0

    def read_previous_experience(self) -> dict[str, object]:
        """Actually dereference the previous motion, without copying to Present."""
        prior = self.previous_motion
        source = prior.cognitive_summary()
        assert self.internal_body.observation is None
        assert self.internal_world.observation is None
        return {
            "classification": self.classification,
            "current_epoch_id": self.internal_body.epoch_id,
            "previous_epoch_id": prior.self_body.epoch_id,
            "same_previous_companion_identity": True,
            "current_body_outcome": None,
            "current_world_observation": "UNKNOWN_NO_NEW_NATIVE_PRESENT",
            "current_body_observation": "UNKNOWN_NO_NEW_NATIVE_PRESENT",
            "current_position_x": None,
            "previous_action_id": prior.action_id,
            "previous_native_ref": self.prior_native_source_ref,
            "previous_paper_world": prior.paper_world_uuid,
            "previous_paper_sha256": prior.paper_source_sha256,
            "previous_input_off_sampled_motion_ticks": source[
                "changed_with_last_reported_input_off"
            ],
            "previous_paper_samples": source["ticks_sampled"],
            "previous_effective_clear_tick": "NOT_ATTESTED",
            "full_tick_input_idle": "NOT_ATTESTED",
            "native_present_acquired_in_this_epoch": False,
            "new_world_or_client_session": False,
            "paper_node_clock_aligned": False,
            "physical_stability_attested": False,
            "goal_admitted": False,
            "p1_wait_granted": 0,
            "l10_pairs_admitted": 0,
            "s10_updates": 0,
            "s11_grants": 0,
            "actions_issued": 0,
            "model_calls": 0,
            "learning_updates": 0,
        }


class PostWorldInternalEpochLease:
    """One prior in-process MotionCompanion, one post-shutdown read, no replay.

    Call `enter_after_owner_shutdown` only after the original host's Node
    and Java process shutdown and its actual original S50 join have succeeded.
    The integers are an OWNER-OBSERVED local-exit check, not independent
    physical source attestation. The lease holds no durable memory.
    """

    def __init__(self, previous: SelfBodyS50MotionCompanion) -> None:
        if not isinstance(previous, SelfBodyS50MotionCompanion):
            raise PostWorldInternalEpochRejected("original typed prior companion required")
        body, outcome = previous.self_body, previous.self_body.outcome
        native = body.observation
        if (
            body.self_id is None
            or native is None or outcome is None
            or native.action_id != previous.action_id
            or native.session_id != body.session_id
            or native.consequence_provenance != outcome.world_provenance
            or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or outcome.reason_code != "observed_execution"
            or outcome.source_status != "executed"
            or outcome.action_id != previous.action_id
            or outcome.session_id != body.session_id
            or previous.world_client_clock_alignment != "NOT_ATTESTED"
            or previous.effective_clear_world_tick != "NOT_ATTESTED"
            or previous.native_present_minted
            or previous.physically_stopped_attested
            or previous.p1_wait_granted
            or len(previous.ticks) != 8
        ):
            raise PostWorldInternalEpochRejected("unqualified prior S16/native/S50 source")
        self._previous: SelfBodyS50MotionCompanion | None = previous
        self._done = False
        self._status = "AWAITING_ORIGINAL_WORLD_SHUTDOWN"
        self._read_count = 0

    def enter_after_owner_shutdown(
        self, *, node_exit: int, java_exit: int, cleanup_errors: bool = False,
    ) -> dict[str, object]:
        """One actual new internal epoch, not a new L0/native decision epoch.

        Fails closed if the caller has not observed both process exits.
        This adapter cannot inspect external PID/port and never claims it did.
        """
        if self._done or self._previous is None:
            raise PostWorldInternalEpochRejected("internal epoch lease already consumed")
        prior = self._previous
        self._done = True
        self._previous = None
        if (
            type(node_exit) is not int or node_exit != 0
            or type(java_exit) is not int or java_exit != 0
            or type(cleanup_errors) is not bool or cleanup_errors
        ):
            self._status = "REJECTED_WORLD_NOT_CLOSED"
            raise PostWorldInternalEpochRejected("original Node/Java exit not successful")
        try:
            old = prior.self_body
            assert old.observation is not None
            epoch_id = (
                f"internal-after-closed-world-{old.observation.native_seq}-"
                f"{prior.action_id}"
            )
            if epoch_id == old.epoch_id:
                raise PostWorldInternalEpochRejected("internal epoch was not advanced")
            # Existing SelfBody/SelfWorld owner APIs, deliberately NO new Present.
            new_body = compose_self_body_view(
                self_id=old.self_id,
                session_id=old.session_id,
                epoch_id=epoch_id,
            )
            new_world = compose_self_world_view(
                self_id=old.self_id,
                session_id=old.session_id,
                epoch_id=epoch_id,
                self_body=new_body,
            )
            if (
                new_body.observation is not None
                or new_body.outcome is not None
                or new_world.observation is not None
                or new_world.self_body is not new_body
                or new_body.observed("position_x").origin is not BodyOrigin.UNKNOWN
            ):
                raise PostWorldInternalEpochRejected("prior physics leaked into Present")
            readout = PostWorldInternalEpochReadout(
                internal_body=new_body,
                internal_world=new_world,
                previous_motion=prior,
                prior_native_source_ref=old.observation.source_ref,
            )
            summary = readout.read_previous_experience()
            if summary["current_position_x"] is not None:
                raise PostWorldInternalEpochRejected("invented post-shutdown position")
            self._read_count = 1
            self._status = "INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_ONCE"
            return summary
        except Exception:
            self._status = "REJECTED_INTERNAL_EPOCH_SOURCE"
            raise

    def status(self) -> dict[str, object]:
        return {
            "status": self._status,
            "internal_epoch_reads": self._read_count,
            "original_native_probes_requested": 0,
            "new_world_sessions": 0,
            "new_action_issuers": 0,
            "model_calls": 0,
            "memory_writes": 0,
            "p1_wait_granted": 0,
            "l10_pairs_admitted": 0,
            "s10_updates": 0,
            "s11_grants": 0,
            "science_qualified": False,
        }

    def close(self) -> None:
        self._done = True
        self._previous = None
        if self._status == "AWAITING_ORIGINAL_WORLD_SHUTDOWN":
            self._status = "EXPIRED_NO_WORLD_SHUTDOWN"
