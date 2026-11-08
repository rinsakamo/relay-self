"""D14 R6: source-bound original S49 MOVE admission in one natural World.

Captures only actual unsolicited Mineflayer entities frames. Frozen S49
L0/S14, the original NormalSessionActionExecutor and the existing durable
C1 physical MOVE fence remain authoritative. S15 clear is NOT physical STOP.
This DEV lane does not rearm Intents or authorize post-MOVE EAT.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s34_native_world_cognition_ci import (
    S34EvidenceFailure,
    _native_epoch_two,
    _native_threat,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.execution_binding import ExecutionBinding, resolve_execution_binding
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant, ReactiveL0Rejected
from relay_self.world_conditioned_choice import WorldChoiceKind, WorldChoiceRejected

MAX_EVENT_BUFFER = 64
MAX_NATIVE_SEQ_LAG = 128


class NaturalMotionRejected(RuntimeError):
    """R6 cannot claim original native/S14/Action source or physical closure."""


class NaturalOriginalS49Motion:
    """A non-issuing capture attached to the SAME original S49 Action owner."""

    def __init__(
        self, session_id: str, intent: IntentCommitment,
        executor: NormalSessionActionExecutor, evidence_dir: Path,
    ) -> None:
        if (
            executor.session_id != session_id or executor.intent is not intent
            or intent.current_intent is None
        ):
            raise NaturalMotionRejected("FOREIGN_ORIGINAL_S49_OWNER")
        # Reuse the exact frozen S49 governed retained source, not a new
        # hand-authored S14 score or an L1 learning update.
        _, committed, _, _, _, _ = s19._epoch_one()
        retained = committed.new_state
        if (
            retained.target_id != "risk_weight"
            or retained.revision != 1 or retained.value != 4
        ):
            raise NaturalMotionRejected("UNQUALIFIED_FROZEN_S49_S10_OWNER")
        self.sid = session_id
        self.intent = intent
        self.executor = executor
        self.host = NormalWorldL0(
            session_id, intent.current_intent.intent_id,
            retained, max_events=32, max_action_requests=32,
        )
        self.fence = OriginalS49PhysicalFence.create(
            evidence_dir / "original_s49_motion_fence.json",
            self_id="s49-original-self",
        )
        self.events: deque[MineflayerObservation] = deque(maxlen=MAX_EVENT_BUFFER)
        self.seen_event_frames = 0

    def capture_event(self, frame: MineflayerObservation) -> None:
        """Record raw event as received; never reinterpret a probe as event."""
        if not isinstance(frame, MineflayerObservation) or frame.kind != "entities":
            raise NaturalMotionRejected("ONLY_NATIVE_ENTITIES_EVENTS_CAN_BE_CAPTURED")
        if (
            frame.session_id != self.sid or frame.request_id is not None
            or frame.provenance.source != "mineflayer"
            or frame.snapshot.nearby_entities_coverage.truncated
        ):
            raise NaturalMotionRejected("INVALID_NATIVE_ENTITY_EVENT_SOURCE")
        if self.events and frame.seq <= self.events[-1].seq:
            raise NaturalMotionRejected("REPLAYED_OR_REORDERED_ENTITY_EVENT")
        self.seen_event_frames += 1
        self.events.append(frame)

    def current_candidate(
        self, probe: MineflayerObservation,
    ) -> MineflayerObservation | None:
        """Return a real source event only after frozen S49 admission succeeds."""
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.session_id != self.sid or probe.kind != "probe"
            or not probe.request_id or probe.provenance.source != "mineflayer"
            or probe.snapshot.nearby_entities_coverage.truncated
            or probe.snapshot.health <= 0 or probe.snapshot.oxygen_level == 0
        ):
            return None
        zombies = [e for e in probe.snapshot.nearby_entities if e.name == "zombie"]
        if len(zombies) != 1 or not 0.1 <= zombies[0].distance < 4.0:
            return None
        for event in reversed(self.events):
            if (
                event.seq <= self.host._last_seq or event.seq >= probe.seq
                or probe.seq - event.seq > MAX_NATIVE_SEQ_LAG
            ):
                continue
            try:
                choice = self.host._check(event, probe)
            except (ReactiveL0Rejected, S34EvidenceFailure, WorldChoiceRejected):
                continue
            if choice.selection is WorldChoiceKind.MOVE_AWAY:
                return event
        return None

    def _operator_grants(self, step: Any):
        if step.grant is None or self.intent.current_intent is None:
            raise NaturalMotionRejected("NO_CURRENT_S49_MOVE_GRANT")
        common = {
            "intent_id": step.grant.intent_id,
            "session_id": self.sid,
            "action_id": step.action_request_id,
            "event_seq": step.event_seq,
            "probe_seq": step.choice.probe_seq,
            "entity_id": step.choice.entity_id,
            "granted": True,
        }
        return tuple(
            NormalActionAuthorization(
                **common,
                stage=stage,
                authority_id=(
                    f"d14-r6-operator-{stage.value.lower()}-{step.event_seq}"
                ),
                provenance=Provenance(
                    "d14-r6-explicit-operator-dev-scope",
                    f"{stage.value.lower()}:{step.event_seq}:{step.choice.probe_seq}",
                ),
            )
            for stage in (NormalActionStage.PROPOSE, NormalActionStage.ISSUE)
        )

    async def issue_original_move(
        self, session: Any, event: MineflayerObservation,
        probe: MineflayerObservation, *, cycle: int,
    ) -> dict[str, object]:
        """One issuer; pre-ISSUE fsync precedes physical command. Never replay."""
        if (
            event is not self.current_candidate(probe)
            or session.started.session_id != self.sid
            or session.process_returncode is not None
            or self.executor.supervisor.open_actions
            or self.fence.unresolved
            or self.intent.current_intent is None
        ):
            raise NaturalMotionRejected("NO_CURRENT_REAL_NATIVE_MOVE_CANDIDATE")
        action_id = f"d14-r6-s49-move-{cycle}-{self.sid}"
        grant = L0ActionGrant(
            authority_id=f"d14-r6-independent-grant-{cycle}",
            action_id=action_id,
            intent_id=self.intent.current_intent.intent_id,
            session_id=self.sid, event_seq=event.seq, probe_seq=probe.seq,
            entity_id=self.host._check(event, probe).entity_id,
            granted=True,
            provenance=Provenance(
                "d14-r6-explicit-operator-dev-scope",
                f"grant:{cycle}:{event.seq}:{probe.seq}",
            ),
        )
        step = self.host.decide(event, probe, grant=grant)
        if step.choice.selection is not WorldChoiceKind.MOVE_AWAY:
            raise NaturalMotionRejected("FROZEN_S49_L0_DID_NOT_SELECT_MOVE")
        native = _native_threat(
            probe, probe.request_id,
            expected_entity_id=step.choice.entity_id,
        )
        outputs, epoch = _native_epoch_two(
            ActionSupervisor(), self.intent, self.host.retained,
            self.host.retained, expected_revision=self.host.retained.revision,
            native=native, required_intent_id=step.grant.intent_id,
        )
        if (
            epoch.cognition_requested
            or outputs["plan"].selected is None
            or outputs["plan"].selected.candidate_id != "MOVE_AWAY"
            or outputs["admission"].status.value != "admitted"
            or outputs["policies"][-2].required_intent_id != step.grant.intent_id
        ):
            raise NaturalMotionRejected("S14_ORIGINAL_NATIVE_MOTION_NOT_ADMITTED")
        binding = ExecutionBinding(
            binding_id=f"d14-r6-binding-{event.seq}",
            candidate_ref="MOVE_AWAY",
            required_intent_id=step.grant.intent_id,
            skill_execution_id=f"d14-r6-skill-{event.seq}",
            skill_ref="escape-movement",
            action_id=action_id,
            action_ref="MOVE_BACKWARD",
            provenance=Provenance("d14-r6-execution-binding", action_id),
        )
        bound = resolve_execution_binding(
            outputs["admission"], outputs["control"], outputs["route"],
            self.intent, outputs["policies"][-2], binding,
            provenance=Provenance("d14-r6-s14-admitted", action_id),
        )
        propose, issue = self._operator_grants(step)
        self.executor.require_authorizations(step, bound, probe, propose, issue)
        self.fence.require_clear()
        receipt = await self.executor.execute(
            session, step, bound, probe, propose, issue,
            pre_issue_reservation=lambda: self.fence.prepare(
                session_id=self.sid, intent_id=step.grant.intent_id,
                action_id=action_id, probe=probe,
            ),
        )
        if receipt.terminal.state is not ActionState.OUTCOME:
            raise NaturalMotionRejected("ORIGINAL_S49_MOVE_S16_NOT_OUTCOME")
        self.fence.close(
            receipt, probe, original_supervisor=self.executor.supervisor,
        )
        return {
            "action_id": action_id,
            "kind": "MOVE_AWAY",
            "terminal": receipt.terminal.state.value,
            "session_id": self.sid,
            "native_event_seq": event.seq,
            "native_admitted_seq": probe.seq,
            "movement_m": receipt.consequence.movement_distance,
            "original_move_fence_sha256": self.fence.sha256,
            "s15_clear_ack": "ORIGINAL",
            "effective_physical_stop": "UNATTESTED",
            "post_move_eat_granted": False,
            "interpretation": "ORIGINAL_S16_OUTCOME_NOT_EFFECTIVE_STOP",
        }
