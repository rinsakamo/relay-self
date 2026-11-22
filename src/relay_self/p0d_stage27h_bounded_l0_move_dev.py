"""Stage27h DEV: one immutable MOVE Invocation, finite CPU L0 action loop.

The L0 loop owns neither new model choice nor physical execution authority.
It validates each original physical issuer's settled Action/WAL source and
decides whether the *same* bound Skill needs another short Action. Every
child still goes through the original ActionPort/STOP/WAL/PhysicalIssueAdmission.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from relay_self.action import ActionState
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation
from relay_self.target_contract import (
    TargetBodyObservation,
    TargetConditionStatus,
    evaluate_target,
)

STAGE27H_SETTLING_PROBE_RESERVATION = 60
# Sufficient STOP/settling probe requests are reserved BEFORE each physical
# MOVE. This upper bound is consumed pessimistically until a canonical terminal
# Action and its complete native all_stop_probes source are verified.


class Stage27hLoopRefusal(RuntimeError):
    """Unsafe/stale original L0 MOVE continuation, never a new grant."""


@dataclass(frozen=True, slots=True)
class Stage27hLoopStep:
    status: str
    target_status: str
    target_gap_m: float | None
    action_count: int
    observation_count: int
    cumulative_distance_m: float
    last_native_seq: int
    last_action_id: str | None
    terminal_wal_sha256: str
    skill_succeeded: bool = False
    goal_succeeded: bool = False
    extra_physical_authority: bool = False


class Stage27hBoundedMoveLoop:
    """L0 parent for sequential one-shot original Action interpreters.

    It deliberately does NOT restart a process-local cursor. Each physical
    child is compiled by the existing Stage27c interpreter using the same
    original, immutable Invocation. The parent tracks cumulative limits.
    A restart cannot re-create this parent's original identity from a WAL.
    """

    def __init__(
        self,
        prepared: PreparedStage26L1,
        handoff: Stage27OwnedMoveIntent,
        *,
        owner: CheckpointedCognitiveOwner,
        physical: PhysicalIssueAdmission,
        world_epoch: int,
        start_ns: int,
    ) -> None:
        if (
            not isinstance(prepared, PreparedStage26L1)
            or not isinstance(handoff, Stage27OwnedMoveIntent)
            or not isinstance(owner, CheckpointedCognitiveOwner)
            or not isinstance(physical, PhysicalIssueAdmission)
            or type(start_ns) is not int or start_ns < 0
            or type(world_epoch) is not int or world_epoch != prepared.world_epoch
            or handoff.world_epoch != world_epoch
            or len(prepared.round.frame.options) != 1
        ):
            raise Stage27hLoopRefusal("original bounded MOVE scope unavailable")
        inv = prepared.round.frame.options[0].invocation
        if (
            not isinstance(inv, SkillInvocation)
            or inv.skill_id != "MOVE" or inv.goal_id != "EXPLORE_WORLD"
            or inv.target.kind != "DESTINATION" or inv.target.contract is None
            or inv.parameter_preset_ref is None
            or inv.invocation_ref != handoff.invocation_ref
            or inv.parameter_preset_ref != handoff.preset_ref
            or inv.budget.max_actions not in (2, 3, 4)
            or inv.budget.max_distance_m is None
            or inv.budget.max_observations < inv.budget.max_actions * (
                1 + STAGE27H_SETTLING_PROBE_RESERVATION
            )
        ):
            raise Stage27hLoopRefusal(
                "explicit bounded multi-Action MOVE Preset/Target required"
            )
        self.prepared = prepared
        self.handoff = handoff
        self.owner = owner
        self.physical = physical
        self.invocation = inv
        self.world_epoch = world_epoch
        self.start_ns = start_ns
        self.action_count = 0
        self.observation_count = 0
        self.cumulative_distance_m = 0.0
        self.last_native_seq = -1
        self.last_action_id: str | None = None
        self.last_wal_digest = ""
        self.terminal_status: str | None = None
        self._seen_action_ids: set[str] = set()
        self._source_seq = -1
        self._ready_to_reserve_seq: int | None = None
        self._reserved_source_seq: int | None = None
        self._settlement_reserved = 0
        self._validate_owner_and_journal()

    def _validate_owner_and_journal(self) -> PhysicalActionJournal:
        owner, physical, prep, handoff = (
            self.owner, self.physical, self.prepared, self.handoff,
        )
        if (
            owner is not prep.original_owner
            or owner.self_id != prep.self_id
            or owner.native_session_id != prep.native_session
            or owner.fresh_native_observation_required
            or handoff.self_id != prep.self_id
            or handoff.native_session_id != prep.native_session
            or not physical.resident_mode or physical.closed
            or physical.active_action_ids
            or physical.current_native_sessions.get(owner.self_id)
            != prep.native_session
            or physical.resident_states.get(owner.self_id) != "ONLINE"
            or owner.intent.current_intent is None
            or owner.intent.current_intent.intent_id != handoff.intent_id
            or owner.intent.pending_reconsideration is not None
            or owner.intent.current_intent.objective != self.invocation.goal_id
        ):
            raise Stage27hLoopRefusal("original live Self/Intent/Physical epoch changed")
        skill = owner.skills.get(handoff.skill_execution_id)
        if (
            skill is None or skill.state is not SkillState.STARTED
            or not skill.is_current_snapshot or skill.intent_id != handoff.intent_id
            or skill.skill_id != self.invocation.skill_id
            or owner.supervisor.open_actions
        ):
            raise Stage27hLoopRefusal("original bound Skill/Action owner changed")
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        if (
            len(journal.records) != self.action_count
            or self.action_count > 0 and journal.digest != self.last_wal_digest
        ):
            raise Stage27hLoopRefusal("canonical multi-Action WAL lineage changed")
        if abs(sum(row["displacement_m"] for row in journal.records)
               - self.cumulative_distance_m) > 1e-6:
            raise Stage27hLoopRefusal("cumulative original MOVE budget counter altered")
        for idx, row in enumerate(journal.records):
            if (
                row["capability"] != "MOVE_PLACE"
                or row["action_id"] not in self._seen_action_ids
                or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                or row["invocation_ref"] != self.invocation.invocation_ref
                or row["preset_ref"] != self.invocation.parameter_preset_ref
                or row["target_contract_ref"]
                != self.invocation.target.contract.contract_ref
                or row["intent_id"] != handoff.intent_id
                or row["skill_execution_id"] != handoff.skill_execution_id
                or row["session_id"] != prep.native_session
                or row.get("gait_mode", "WALK") not in ("WALK", "SNEAK")
                or row["after_seq"] is None
                or idx and row["probe_seq"] <= journal.records[idx-1]["after_seq"]
            ):
                raise Stage27hLoopRefusal("original WAL rows differ from MOVE Skill")
        return journal

    def _assess(
        self, observed: MineflayerObservation, now_ns: int, *,
        newly_requested: int = 1, next_preflight_required: bool = False,
    ) -> Stage27hLoopStep:
        if (
            self.terminal_status is not None
            or type(newly_requested) is not int
            or newly_requested not in (0, 1)
            or type(next_preflight_required) is not bool
            or type(now_ns) is not int or now_ns < self.start_ns
            or not isinstance(observed, MineflayerObservation)
            or observed.kind != "probe" or not observed.request_id
            or observed.session_id != self.prepared.native_session
            or observed.provenance.source != "mineflayer"
            or observed.provenance.reference
            != f"{observed.session_id}:{observed.seq}"
            or observed.seq <= self._source_seq
            or observed.snapshot.time is None
            or observed.snapshot.health <= 0
            or observed.snapshot.oxygen_level == 0
        ):
            raise Stage27hLoopRefusal("stale/unsafe MOVE WorldBody observation")
        self._source_seq = observed.seq
        self.observation_count += newly_requested
        if self.observation_count > self.invocation.budget.max_observations:
            raise Stage27hLoopRefusal(
                "Invocation native probe budget exceeded, no further Action"
            )
        target = self.invocation.target.contract
        assert target is not None
        assessment = evaluate_target(
            target, TargetBodyObservation(
                scope=self.invocation.scope, seq=observed.seq,
                provenance=observed.provenance,
                position=observed.snapshot.position,
            ),
        )
        limit = self.invocation.budget
        timed_out = (now_ns - self.start_ns) >= limit.max_duration_ms * 1_000_000
        budget_exhausted = (
            self.action_count >= limit.max_actions
            # Reserve the full STOP settlement quota before any next MOVE.
            # After a terminal Action, an additional *preflight* native probe
            # will be needed before a new reservation.
            or self.observation_count + STAGE27H_SETTLING_PROBE_RESERVATION
            + int(next_preflight_required) > limit.max_observations
            or self.cumulative_distance_m >= limit.max_distance_m
            or timed_out
        )
        if assessment.status is TargetConditionStatus.CONDITION_OBSERVED:
            status = "L0_TARGET_REACHED_YIELD_EVALUATION"
        elif assessment.status is not TargetConditionStatus.OUTSIDE:
            status = "L0_WORLD_CONDITION_YIELD_EVALUATION"
        elif budget_exhausted:
            status = "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        else:
            status = "L0_CONTINUE_MOVE"
        if status != "L0_CONTINUE_MOVE":
            self.terminal_status = status
        self._ready_to_reserve_seq = (
            observed.seq if status == "L0_CONTINUE_MOVE"
            and not next_preflight_required else None
        )
        return Stage27hLoopStep(
            status, assessment.status.value, assessment.gap_to_envelope_m,
            self.action_count, self.observation_count, self.cumulative_distance_m,
            observed.seq, self.last_action_id, self.last_wal_digest,
        )

    def pre_action(
        self, observed: MineflayerObservation, *, now_ns: int,
    ) -> Stage27hLoopStep:
        """L0 preflight: no physical proposal if the new source is unsafe."""
        if self._settlement_reserved or self._reserved_source_seq is not None:
            # A prior physical Action was issued but its complete canonical
            # STOP/settlement readback was not accepted. Do not even attempt
            # to requalify a new preflight or reinterpret its WAL as clear.
            raise Stage27hLoopRefusal(
                "L0 settling reservation unresolved: no second MOVE"
            )
        self._validate_owner_and_journal()
        if self.last_native_seq >= 0 and observed.seq <= self.last_native_seq:
            raise Stage27hLoopRefusal("next native observation not after prior STOP")
        return self._assess(observed, now_ns)

    def reserve_settling_observations(
        self, *, source_probe: MineflayerObservation,
    ) -> int:
        """Precommit maximum native STOP probes BEFORE issuing any motion.

        Physical issuer must use the returned cap. On uncertain STOP/WAL the
        reservation stays consumed and the whole trial holds (no retry).
        Only verified terminal receipt may refund the unused probe slots.
        """
        self._validate_owner_and_journal()
        cap = STAGE27H_SETTLING_PROBE_RESERVATION
        if (
            self.terminal_status is not None
            or self._settlement_reserved != 0
            or self._reserved_source_seq is not None
            or not isinstance(source_probe, MineflayerObservation)
            or self._ready_to_reserve_seq is None
            or source_probe.seq != self._ready_to_reserve_seq
            or source_probe.session_id != self.prepared.native_session
            or self.observation_count + cap
            > self.invocation.budget.max_observations
        ):
            raise Stage27hLoopRefusal(
                "L0 STOP observation reservation unavailable; do not issue"
            )
        self.observation_count += cap
        self._settlement_reserved = cap
        self._reserved_source_seq = source_probe.seq
        self._ready_to_reserve_seq = None
        return cap

    def observe_terminal_action(
        self,
        receipt: Stage27PlaceMoveReceipt,
        *,
        source_probe: MineflayerObservation,
        now_ns: int,
    ) -> Stage27hLoopStep:
        """Read back issuer's terminal parent Action and canonical appended WAL."""
        if (
            self.terminal_status is not None
            or not isinstance(receipt, Stage27PlaceMoveReceipt)
            or not isinstance(source_probe, MineflayerObservation)
            or type(now_ns) is not int
            or now_ns < self.start_ns
            or self.action_count >= self.invocation.budget.max_actions
            or receipt.action_id in self._seen_action_ids
            or self._settlement_reserved != STAGE27H_SETTLING_PROBE_RESERVATION
            or self._reserved_source_seq != source_probe.seq
            or receipt.native_session_id != self.prepared.native_session
            or receipt.original_invocation_ref != self.invocation.invocation_ref
            or receipt.original_preset_ref != self.invocation.parameter_preset_ref
            or receipt.target_contract_ref
            != self.invocation.target.contract.contract_ref
            or receipt.l0_step_status != "YIELD_EVALUATION"
            or receipt.skill_success_attested or receipt.l0_goal_succeeded
            or receipt.paper_causal_attribution or not receipt.native_effect_issued
            or source_probe.seq != self._source_seq
            or receipt.settled_probe.seq <= source_probe.seq
            or receipt.settled_probe.session_id != self.prepared.native_session
            or not math.isfinite(receipt.displacement_m)
            or receipt.displacement_m < 0
        ):
            raise Stage27hLoopRefusal("Action was not next original MOVE child")
        stop_probes = receipt.all_stop_probes
        if (
            not isinstance(stop_probes, tuple)
            or not 3 <= len(stop_probes) <= self._settlement_reserved
            or stop_probes[0] != receipt.initial_stop_probe
            or stop_probes[-1] != receipt.settled_probe
            or receipt.first_stable_probe not in stop_probes
            or len({p.request_id for p in stop_probes}) != len(stop_probes)
            or any(
                not isinstance(p, MineflayerObservation)
                or p.kind != "probe" or not p.request_id
                or p.session_id != self.prepared.native_session
                or p.provenance.source != "mineflayer"
                or p.provenance.reference != f"{p.session_id}:{p.seq}"
                or p.snapshot.time is None or p.snapshot.health <= 0
                or p.seq <= source_probe.seq
                or idx and p.seq <= stop_probes[idx - 1].seq
                for idx, p in enumerate(stop_probes)
            )
        ):
            raise Stage27hLoopRefusal(
                "STOP probes not fully accounted: original source unqualified"
            )
        owner, journal = self.owner, PhysicalActionJournal.restore(
            self.owner.files.physical_wal_file, self_id=self.owner.self_id,
        )
        journal.require_clear()
        row = journal.records[-1] if journal.records else None
        action = owner.supervisor.get(receipt.action_id)
        if (
            len(journal.records) != self.action_count + 1
            or abs(sum(r["displacement_m"] for r in journal.records[:-1])
                   - self.cumulative_distance_m) > 1e-6
            or row is None or row["action_id"] != receipt.action_id
            or row["status"] != receipt.journal_status
            or row["capability"] != "MOVE_PLACE"
            or row["invocation_ref"] != self.invocation.invocation_ref
            or row["preset_ref"] != self.invocation.parameter_preset_ref
            or row["target_contract_ref"]
            != self.invocation.target.contract.contract_ref
            or row["intent_id"] != self.handoff.intent_id
            or row["skill_execution_id"] != self.handoff.skill_execution_id
            or row["session_id"] != self.prepared.native_session
            or row["probe_seq"] != source_probe.seq
            or row["probe_request_id"] != source_probe.request_id
            or row["after_seq"] != receipt.settled_probe.seq
            or row.get("gait_mode", "WALK") != receipt.gait_mode
            or row.get("gait_ack_seq") != (
                receipt.gait_control_ack.seq
                if receipt.gait_control_ack is not None else None
            )
            or journal.digest != receipt.journal_sha256
            or action.state is not ActionState.OUTCOME
            or not action.is_current_snapshot
            or action.intent_id != self.handoff.intent_id
            or action.skill_execution_id != self.handoff.skill_execution_id
            or abs(row["displacement_m"] - receipt.displacement_m) > 1e-5
        ):
            raise Stage27hLoopRefusal("original terminal Action/WAL relation missing")
        # The terminal Action is the last new row, but historic rows must
        # remain canonical; on any interruption this parent cannot resume.
        self.action_count += 1
        self.cumulative_distance_m += receipt.displacement_m
        self.last_native_seq = receipt.settled_probe.seq
        self.last_action_id = receipt.action_id
        self.last_wal_digest = journal.digest
        self._seen_action_ids.add(receipt.action_id)
        # Until this verified terminal Action, the entire STOP quota was
        # pessimistically counted. Release only the unused reservation.
        self.observation_count -= self._settlement_reserved - len(stop_probes)
        self._settlement_reserved = 0
        self._reserved_source_seq = None
        if receipt.journal_status == "NATIVE_PLACE_MOVE_OVERSHOOT":
            self.terminal_status = "L0_OVERSHOOT_YIELD_EVALUATION"
        elif receipt.journal_status != "NATIVE_PLACE_MOVE_SETTLED":
            self.terminal_status = "L0_NO_PROGRESS_YIELD_EVALUATION"
        elif self.cumulative_distance_m > self.invocation.budget.max_distance_m + 1e-6:
            self.terminal_status = "L0_CUMULATIVE_OVERSHOOT_YIELD_EVALUATION"
        if self.terminal_status is not None:
            return Stage27hLoopStep(
                self.terminal_status, "UNASSESSED", None, self.action_count,
                self.observation_count, self.cumulative_distance_m,
                self.last_native_seq, self.last_action_id, self.last_wal_digest,
            )
        self._validate_owner_and_journal()
        # The final settled probe is already included in stop_probes.
        # Target assessment MUST NOT count that same source twice.
        return self._assess(
            receipt.settled_probe, now_ns, newly_requested=0,
            next_preflight_required=True,
        )
