"""E10 caller composition of E3/S24 admission and existing S14-S16 owners.

No launch entrypoint: the caller supplies an already-owned Action3 and session.
Offline doubles establish wiring only, never physical source authentication.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Callable

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerMessage,
    MineflayerObservation,
    encode_observe,
)
from experiments.epistemic_e3_s29_integration import (
    EpistemicResult,
    _first_for_arm,
    continue_with_existing_owners,
    plan_epistemic,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.correlated_probe import (
    CorrelatedProbeGrant,
    CorrelatedProbeReceipt,
    request_correlated_post_action_probe,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    ExecutionBindingResult,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.provenance import Provenance
from relay_self.second_epoch_action import require_fresh_second_consequence
from relay_self.skill import SkillExecution, SkillState


class E10Rejected(ValueError):
    """Exact owner, stream, time or arm isolation failed."""


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Strictly later, read-only native sample; never passed into E0/S24."""

    request_id: str
    requested_at_ns: int
    received_at_ns: int
    observation: MineflayerObservation | None
    damage_points: float | None
    movement_m: float | None
    error: str | None


@dataclass(frozen=True, slots=True)
class EpisodeReceipt:
    reset_id: str
    parent_action: ActionLifecycle
    parent_consequence: WorldConsequence
    first_probe: CorrelatedProbeReceipt | None
    decision: EpistemicResult
    decision_at_ns: int
    action4: ActionLifecycle | None
    binding4: ExecutionBindingResult | None
    consequence4: WorldConsequence | None
    interpretation4: ActionOutcomeInterpretation | None
    evaluation: Evaluation
    elapsed_ms: float
    probe_ms: float
    evaluator_ms: float
    evaluator_horizon_ns: int
    native_frames: tuple[MineflayerMessage, ...]
    physically_authenticated: bool = False


class _ExclusiveSession:
    """Single experiment-local reader preserving original native seq/objects."""

    def __init__(self, adapter, session_id: str, next_seq: int):
        self.adapter = adapter
        self.started = adapter.started
        self.session_id = session_id
        self.next_seq = next_seq
        self.phase = "policy"
        self.expected_effects: dict[str, str] = {}
        self.rejection: E10Rejected | None = None
        self.probe_started_ns: int | None = None
        self.probe_ms = 0.0
        self.frames: list[MineflayerMessage] = []
        self.pending_probe = False
        self.request_id: str | None = None

    async def send_observe(self, request_id=None):
        self.pending_probe = True
        self.request_id = request_id
        if self.phase == "policy":
            self.probe_started_ns = perf_counter_ns()
        await self.adapter.send_observe(request_id)

    async def receive(self):
        message = await self.adapter.receive()
        if (
            not isinstance(message, MineflayerMessage)
            or message.session_id != self.session_id
            or message.seq != self.next_seq
        ):
            self.rejection = E10Rejected("native session/seq mismatch or replay")
            raise self.rejection
        self.next_seq += 1
        self.frames.append(message)
        if isinstance(message, MineflayerObservation) and message.kind == "probe":
            if not self.pending_probe or message.request_id != self.request_id:
                self.rejection = E10Rejected("probe request crossed policy/execution/evaluator phase")
                raise self.rejection
            self.pending_probe = False
        if isinstance(message, MineflayerEffectResult):
            if self.expected_effects.get(message.action_id) != message.effect:
                self.rejection = E10Rejected("unknown Action owner/effect in source stream")
                raise self.rejection
            del self.expected_effects[message.action_id]
        if (self.phase == "policy" and isinstance(message, MineflayerObservation)
                and message.kind == "probe" and self.probe_started_ns is not None):
            self.probe_ms += (perf_counter_ns() - self.probe_started_ns) / 1e6
        return message

    async def send_set_control(self, action_id, *, control, state):
        if self.phase != "execution":
            raise E10Rejected("effect outside issued execution")
        self.expected_effects[action_id] = "set_control"
        await self.adapter.send_set_control(action_id, control=control, state=state)

    async def send_clear_controls(self, action_id):
        if self.phase != "execution":
            raise E10Rejected("cleanup outside issued execution")
        self.expected_effects[action_id] = "clear_controls"
        await self.adapter.send_clear_controls(action_id)


def _time(clock, floor: int) -> int:
    value = clock()
    if type(value) is not int or value <= floor:
        raise E10Rejected("clock must strictly follow prior event")
    return value


async def _evaluate(session, baseline, request_id, *, after_ns, clock, timeout_s):
    requested = _time(clock, after_ns)
    session.phase = "evaluator"
    observation = None
    error = None
    try:
        await session.send_observe(request_id)
        # Evaluator is a separate late request, not a threat projection/policy input.
        async def read_sample():
            for _ in range(4):
                message = await session.receive()
                if isinstance(message, MineflayerEffectResult):
                    # Only the exact outstanding cleanup can reach here, after
                    # exclusive stream ownership has checked its identity.
                    if message.effect != "clear_controls":
                        raise E10Rejected("late dispatch in evaluator stream")
                    continue
                if isinstance(message, MineflayerObservation):
                    if message.kind != "probe":
                        continue
                    if message.request_id != request_id:
                        raise E10Rejected("independent evaluator request mismatch")
                    return message
                raise E10Rejected("unexpected evaluator native frame")
            raise EOFError("evaluator sample unavailable within frame bound")
        observation = await asyncio.wait_for(read_sample(), timeout_s)
    except E10Rejected:
        raise
    except (TimeoutError, EOFError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        observation = None
    received = _time(clock, requested)
    damage = movement = None
    if observation is not None:
        damage = baseline.snapshot.health - observation.snapshot.health
        a, b = baseline.snapshot.position, observation.snapshot.position
        movement = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
    return Evaluation(request_id, requested, received, observation, damage, movement, error)


async def run_episode(
    *, arm: str, price_quarters: int, prior_ref: str,
    adapter, action_adapter, cursor: ExclusiveProbeCursor, grant: CorrelatedProbeGrant,
    second_grant: CorrelatedProbeGrant,
    supervisor: ActionSupervisor, action: ActionLifecycle, consequence: WorldConsequence,
    recovery_skill: SkillExecution, intent: IntentCommitment,
    retained: LearningPreferenceState, observed_at_ns: int, inspected_at_ns: int,
    at_ns: int, provenance: Provenance,
    second_observed_at_ns: int, second_inspected_at_ns: int,
    binding4: ExecutionBinding, authorize4: Callable[[ActionLifecycle], ActionLifecycle],
    deadline_ns: int, evaluator_request_id: str, reset_id: str,
    used_sessions: set[str], used_resets: set[str],
    clock: Callable[[], int] = perf_counter_ns, max_age_ns: int = 5,
    timeout_s: float = 0.05, evaluator_horizon_ns: int = 1_000_000_000,
) -> EpisodeReceipt:
    """One exclusive Action3 -> E3/S24 -> authorized Action4/WAIT -> evaluator.

    Session/reset sets are caller-owned consumed identities across trial arms.
    Both probes use the terminal Action3 source. Action4 uses the separately
    scoped S15 session required by the frozen E5 auditor. No reconnect is owned
    here; matching declared config is not proof of physical avatar continuity.
    The explicit authority callback may authorize or deny PROPOSED Action4; it
    sees no evaluator data. UNAVAILABLE preserves S16's open ISSUED state and
    services its deadline before evaluator sampling. No retry or arm loop.
    """
    if type(evaluator_horizon_ns) is not int or evaluator_horizon_ns <= 0:
        raise E10Rejected("fixed positive evaluator horizon required")
    encode_observe(evaluator_request_id)
    if (not evaluator_request_id or evaluator_request_id in (grant.request_id, second_grant.request_id)
            or grant.request_id == second_grant.request_id):
        raise E10Rejected("distinct evaluator request identity required")
    if prior_ref != "uniform-nearfar-v1":
        raise E10Rejected("only frozen predeclared prior allowed")
    if not isinstance(reset_id, str) or not reset_id.strip():
        raise E10Rejected("independent reset identity required")
    if (
        action.state is not ActionState.OUTCOME or not action.is_current_snapshot
        or supervisor.get(action.action_id) is not action or supervisor.open_actions
        or consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.action_id != action.action_id
        or consequence.provenance != action.events[-1].provenance
        or consequence.after_observation is None
        or consequence.after_observation.session_id != consequence.session_id
        or adapter.started.session_id != consequence.session_id
        or cursor.session_id != consequence.session_id
        or cursor.next_seq != consequence.after_observation.seq + 1 or cursor.consumed
        or grant.authority.parent_action_id != action.action_id
        or grant.authority.session_id != consequence.session_id
        or not recovery_skill.is_current_snapshot or recovery_skill.state is not SkillState.STARTED
        or action.skill_execution_id != recovery_skill.execution_id
        or intent.current_intent is None or intent.pending_reconsideration is not None
        or action.intent_id != intent.current_intent.intent_id
        or recovery_skill.intent_id != action.intent_id
    ):
        raise E10Rejected("exact terminal Action3/World/session/read ancestry required")
    native3 = (consequence.before_observation, consequence.dispatch_receipt,
               consequence.cleanup_receipt, consequence.after_observation)
    if (any(item.session_id != consequence.session_id for item in native3)
            or any(a.seq >= b.seq for a, b in zip(native3, native3[1:]))
            or consequence.dispatch_receipt.action_id != action.action_id
            or consequence.dispatch_receipt.effect != "set_control"
            or consequence.cleanup_receipt.action_id != f"{action.action_id}-s15-clear"
            or consequence.cleanup_receipt.effect != "clear_controls"):
        raise E10Rejected("original Action3 native command/result identity mismatch")
    if consequence.session_id in used_sessions or reset_id in used_resets:
        raise E10Rejected("cross-arm session/reset reuse")
    # A failed or WAIT episode is also consumed; this never creates replay permission.
    used_sessions.add(consequence.session_id)
    used_resets.add(reset_id)
    session = _ExclusiveSession(adapter, consequence.session_id, cursor.next_seq)
    started = clock()
    elapsed_started = perf_counter_ns()
    first_probe = None
    decision_cursor = cursor
    decision_grant = grant
    first = _first_for_arm(arm, plan_epistemic(price_quarters))
    if first == "OBSERVE":
        if (second_observed_at_ns <= inspected_at_ns
                or at_ns < second_inspected_at_ns):
            raise E10Rejected("second source read/decision clock ancestry reversed")
        first_probe = await request_correlated_post_action_probe(
            session, cursor, grant, supervisor, action, consequence,
            observed_at_ns=observed_at_ns, inspected_at_ns=inspected_at_ns,
            max_age_ns=max_age_ns, timeout_s=timeout_s,
        )
        if first_probe.source_receipt.evidence.threat_clearance_cm != 180:
            raise E10Rejected("frozen E5 first source must be far180cm")
        decision_cursor = ExclusiveProbeCursor(consequence.session_id, first_probe.next_cursor_seq)
        decision_grant = second_grant
    decision = await continue_with_existing_owners(
        arm=arm, price_quarters=price_quarters, adapter=session, cursor=decision_cursor, grant=decision_grant,
        supervisor=supervisor, action=action, consequence=consequence,
        recovery_skill=recovery_skill, intent=intent, retained=retained,
        observed_at_ns=second_observed_at_ns, inspected_at_ns=second_inspected_at_ns,
        at_ns=at_ns, provenance=provenance, timeout_s=timeout_s,
        previous_receipt=first_probe, max_age_ns=max_age_ns,
    )
    decision_at = _time(clock, max(started, at_ns))
    probe_ms = session.probe_ms
    action4 = bound4 = world4 = interpretation = None
    execution_session = None
    completed_at = decision_at
    if decision.selected == "MOVE_AWAY":
        trace = decision.epoch
        if trace is None or trace.admission.candidate_ref != "MOVE_AWAY":
            raise E10Rejected("exact typed S24 admission required")
        if (
            binding4.action_id == action.action_id
            or binding4.binding_id == consequence.binding_id
            or binding4.skill_execution_id == recovery_skill.execution_id
            or binding4.action_ref != "MOVE_BACKWARD"
        ):
            raise E10Rejected("distinct Action4/Skill/binding with existing S15 mapping required")
        try:
            supervisor.get(binding4.action_id)
        except UnknownSupervisedAction:
            pass
        else:
            raise E10Rejected("Action4 identity already owned")
        for method in ("send_set_control", "send_clear_controls"):
            if not callable(getattr(action_adapter, method, None)):
                raise E10Rejected("read-only bridge cannot issue an Action")
        if (action_adapter.started.session_id == consequence.session_id
                or action_adapter.started.session_id in used_sessions
                or action_adapter.started.config != adapter.started.config):
            raise E10Rejected("distinct Action4 session with same declared World/avatar config required")
        used_sessions.add(action_adapter.started.session_id)
        execution_session = _ExclusiveSession(action_adapter, action_adapter.started.session_id, 1)
        bound = resolve_execution_binding(
            trace.admission, trace.control, trace.route, intent, trace.admission_criterion,
            binding4, provenance=provenance,
        )
        proposed_at = _time(clock, decision_at)
        if type(deadline_ns) is not int or deadline_ns <= proposed_at:
            raise E10Rejected("invalid Action4 deadline")
        _, proposed, bound4 = start_and_propose_bound_execution(
            bound, intent, at_ns=proposed_at, provenance=provenance,
        )
        authorized = authorize4(proposed)
        if (
            not isinstance(authorized, ActionLifecycle)
            or authorized.state not in (ActionState.AUTHORIZED, ActionState.DENIED)
            or not authorized.is_current_snapshot
            or authorized.events[:-1] != proposed.events
            or proposed.is_current_snapshot
        ):
            raise E10Rejected("separate exact Action4 authorization required")
        if authorized.state is ActionState.DENIED:
            raise E10Rejected("Action4 authority denied; no issue")
        issued_at = _time(clock, max(proposed_at, authorized.events[-1].at_ns))
        issued = supervisor.issue(
            authorized, at_ns=issued_at, deadline_ns=deadline_ns, provenance=provenance,
        )
        command = build_mineflayer_command(issued, bound4)
        execution_session.phase = "execution"
        world4 = await execute_mineflayer_command(
            execution_session, command, timeout_s=timeout_s, provenance=provenance,
        )
        completed_at = _time(clock, issued_at)
        # Execution catches transport errors. Structural contamination still rejects
        # before any S16 promotion and leaves the real issued owner inspectable.
        if execution_session.rejection is not None:
            raise execution_session.rejection
        if completed_at >= deadline_ns:
            supervisor.advance(at_ns=completed_at, provenance=provenance)
            raise E10Rejected("late World result cannot promote terminal OUTCOME")
        require_fresh_second_consequence(
            supervisor, issued, bound4, world4,
            expected_session_id=execution_session.session_id,
            first_session_id=consequence.session_id, at_ns=completed_at,
        )
        interpretation = interpret_world_consequence(
            issued, bound4, world4, provenance=provenance,
        )
        if interpretation.disposition is ActionOutcomeDisposition.UNAVAILABLE:
            # Keep interpretation UNAVAILABLE; terminal TIMEOUT is a separate fact.
            remaining_ns = deadline_ns - clock()
            if remaining_ns > 0:
                await asyncio.sleep(remaining_ns / 1e9)
            completed_at = _time(clock, deadline_ns - 1)
            supervisor.advance(at_ns=completed_at, provenance=provenance)
            action4 = supervisor.get(issued.action_id)
        else:
            action4 = record_interpreted_action_outcome(
                supervisor, interpretation, at_ns=completed_at,
            )
    horizon_at = decision_at + evaluator_horizon_ns
    remaining_ns = horizon_at - clock()
    if remaining_ns > 0:
        await asyncio.sleep(remaining_ns / 1e9)
    evaluator_started = perf_counter_ns()
    evaluation = await _evaluate(
        execution_session or session, consequence.after_observation, evaluator_request_id,
        after_ns=max(completed_at, horizon_at - 1), clock=clock, timeout_s=timeout_s,
    )
    return EpisodeReceipt(
        reset_id, action, consequence, first_probe, decision, decision_at,
        action4, bound4, world4, interpretation, evaluation,
        (perf_counter_ns() - elapsed_started) / 1e6, probe_ms,
        (perf_counter_ns() - evaluator_started) / 1e6,
        evaluator_horizon_ns, tuple(session.frames) + (
            tuple(execution_session.frames) if execution_session is not None else ()
        ),
    )
