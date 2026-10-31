"""DEV route B: prior *provisional* S50 Paper window read at next S49 L0 probe.

The original S49 live_probe callback provides an ALREADY-RECEIVED native
Present. The old S16/native SelfBody view is original typed owner evidence.
The Paper-only provisional window must be independently audited against
full original after shutdown, and the normal complete Node TRACE_END is
still required separately. No new probes, Action, L0 policy writes or P1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    S50LivePaperWindow,
    verify_s50_live_window_against_final_paper,
)
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import SelfBodyView, compose_self_body_view
from relay_self.self_world import SelfWorldView, compose_self_world_view

_ACTION = re.compile(r"s49-native-move-([0-9]+)\Z")
_REQUEST = re.compile(r"s49-actual:([^:]+):event-([0-9]+)\Z")


class LiveNextEpochRejected(ValueError):
    """No valid original next L0 epoch or prior S16 + Paper-only window."""


@dataclass(frozen=True, slots=True)
class LiveNextEpochReadout:
    current_body: SelfBodyView
    current_world: SelfWorldView
    prior_action_id: str
    prior_native_ref: str
    prior_window: S50LivePaperWindow
    classification: str = "LIVE_NEXT_NATIVE_EPOCH_PROVISIONAL_PAPER_READ_ONLY"
    paper_source_finalized: bool = False
    full_node_trace_qualified: bool = False
    l0_choice_modified: bool = False
    extra_native_probes: int = 0
    extra_actions: int = 0
    learning_updates: int = 0

    def read_previous_motion(self) -> dict[str, object]:
        prior = self.prior_window.prior_motion_summary()
        return {
            "classification": self.classification,
            "current_native_ref": self.current_body.observation.source_ref,
            "current_epoch_id": self.current_body.epoch_id,
            "previous_action_id": self.prior_action_id,
            "previous_native_ref": self.prior_native_ref,
            "previous_paper_motion": prior[
                "motion_with_last_reported_input_off_ticks"
            ],
            "previous_paper_sha256": self.prior_window.paper_prefix_sha256,
            "current_native_position_x": self.current_body.observed("position_x").value,
            "previous_paper_not_current_native_present": True,
            "source_status_at_decision": "PROVISIONAL_PAPER_ONLY",
            "full_node_trace_complete": False,
            "paper_node_clock_alignment": "NOT_ATTESTED",
            "effective_clear_tick": "NOT_ATTESTED",
            "physical_stability_attested": False,
            "full_tick_input_idle_attested": False,
            "goal_admitted": False,
            "p1_wait_admitted": 0,
            "l10_pairs": 0,
            "s10_updates": 0,
            "s11_grants": 0,
            "extra_actions": 0,
            "extra_model_calls": 0,
            "learning_updates": 0,
        }


class LiveNextEpochLease:
    """One provisional Paper window, one subsequent genuine S49 probe."""

    def __init__(self, prior_body: SelfBodyView, live_window: S50LivePaperWindow):
        if (
            not isinstance(prior_body, SelfBodyView)
            or not isinstance(live_window, S50LivePaperWindow)
            or not live_window.provisional or live_window.final_source_verified
            or live_window.node_trace_complete
        ):
            raise LiveNextEpochRejected("requires typed prior SelfBody and provisional Paper")
        o, n = prior_body.outcome, prior_body.observation
        action_match = _ACTION.fullmatch(live_window.action_id)
        if (
            o is None or n is None or prior_body.self_id is None
            or action_match is None
            or o.disposition is not ActionOutcomeDisposition.OUTCOME
            or o.source_status != "executed" or o.reason_code != "observed_execution"
            or n.action_id != o.action_id or o.action_id != live_window.action_id
            or n.consequence_provenance != o.world_provenance
            or prior_body.session_id != live_window.session_id
            or n.session_id != live_window.session_id
            or len(live_window.ticks) != 8
        ):
            raise LiveNextEpochRejected("unqualified original S16/native/Paper identity")
        self._last_native_seq = n.native_seq
        self._old_native_ref = n.source_ref
        self._session_id = prior_body.session_id
        self._self_id = prior_body.self_id
        self._prior_action_id = o.action_id
        self._prior_event = int(action_match.group(1))
        self._old_epoch = prior_body.epoch_id
        self._window: S50LivePaperWindow | None = live_window
        self._readout: LiveNextEpochReadout | None = None
        self._status = "WAITING_FOR_NEXT_ORIGINAL_S49_L0_NATIVE_PROBE"
        self._used = False
        self._closed = False
        self._read_count = 0
        self._errors: tuple[str, ...] = ()

    async def observe_original_l0_probe(self, reading: MineflayerObservation) -> None:
        """Callback shape for existing S49 live_probe; NEVER veto original L0."""
        if self._closed or self._used:
            self._revoke("DUPLICATE_OR_EXPIRED")
            return
        self._used = True
        try:
            if not isinstance(reading, MineflayerObservation) or reading.kind != "probe":
                raise LiveNextEpochRejected("native original probe required")
            match = _REQUEST.fullmatch(reading.request_id or "")
            if (
                match is None or match.group(1) != self._session_id
                or int(match.group(2)) <= self._prior_event
                or reading.session_id != self._session_id
                or reading.seq <= self._last_native_seq
            ):
                raise LiveNextEpochRejected("foreign/stale/replayed L0 native source")
            present = project_mineflayer_present(reading)
            current_epoch = f"s49-live-event-{match.group(2)}-native-{reading.seq}"
            if current_epoch == self._old_epoch:
                raise LiveNextEpochRejected("no new native epoch")
            body = compose_self_body_view(
                self_id=self._self_id, session_id=self._session_id,
                epoch_id=current_epoch,
                observation=project_body_present(present),
                minimum_native_seq=self._last_native_seq + 1,
                seen_observation_refs=(self._old_native_ref,),
            )
            world = compose_self_world_view(
                self_id=self._self_id, session_id=self._session_id,
                epoch_id=current_epoch, self_body=body,
                observation=project_self_world_present(
                    present, observer_id=self._self_id,
                ),
                minimum_native_seq=self._last_native_seq + 1,
            )
            if (
                world.self_body is not body
                or world.observation is None
                or body.observation is None
                or world.observation.native_seq != body.observation.native_seq
                or world.observation.provenance != body.observation.source_provenance
                or world.observation.request_id != body.observation.request_id
            ):
                raise LiveNextEpochRejected("Body/World source mismatch")
            window = self._window
            assert window is not None
            self._readout = LiveNextEpochReadout(
                current_body=body, current_world=world,
                prior_action_id=self._prior_action_id,
                prior_native_ref=self._old_native_ref, prior_window=window,
            )
            # Real read at the native decision-boundary observer, not after close.
            self._readout.read_previous_motion()
            self._read_count = 1
            self._status = "NEXT_L0_NATIVE_EPOCH_PAPER_PROVISIONAL_READ"
        except Exception as exc:
            self._revoke(type(exc).__name__)
        finally:
            self._window = None

    def take_once(self) -> LiveNextEpochReadout:
        if (
            self._closed or self._readout is None
            or self._status != "NEXT_L0_NATIVE_EPOCH_PAPER_PROVISIONAL_READ"
        ):
            raise LiveNextEpochRejected("no live next L0 native epoch readout")
        answer = self._readout
        self._readout = None
        self._closed = True
        self._status = "LIVE_NEXT_EPOCH_READOUT_CONSUMED"
        return answer

    def postworld_audit(self, taken: LiveNextEpochReadout, final_paper: bytes) -> dict[str, object]:
        """Historical audit only, cannot retroactively qualify decision-time source."""
        if not isinstance(taken, LiveNextEpochReadout):
            raise LiveNextEpochRejected("missing prior live readout")
        valid = verify_s50_live_window_against_final_paper(
            taken.prior_window, final_paper,
        )
        return {
            "paper_prefix_matches_final_original": valid,
            "l0_read_source_at_decision": "PROVISIONAL_PAPER_ONLY",
            "final_node_trace_still_requires_original_s50_owner": True,
            "l0_decision_modified": False,
            "new_actions": 0,
            "qualification": "DEV_ONLY",
        }

    def _revoke(self, reason: str) -> None:
        self._window = None
        self._readout = None
        self._closed = True
        self._status = "REVOKED_INVALID_NEXT_L0_EPOCH"
        self._errors = (*self._errors, reason)

    def close(self) -> None:
        self._closed = True
        self._window = None
        self._readout = None
        if self._status == "WAITING_FOR_NEXT_ORIGINAL_S49_L0_NATIVE_PROBE":
            self._status = "EXPIRED_WITHOUT_NEXT_NATIVE_L0_EPOCH"

    def status(self) -> dict[str, object]:
        return {
            "status": self._status,
            "next_l0_provisional_paper_reads": self._read_count,
            "errors": self._errors,
            "new_native_probes": 0,
            "new_actions": 0,
            "l0_policy_modified": False,
            "p1_wait": 0,
            "l10_pairs": 0,
            "s10_updates": 0,
            "s11_grants": 0,
            "qualification": "DEV_ONLY",
        }
