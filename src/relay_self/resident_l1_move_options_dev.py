"""Stage24a resident L1: CPU-origin exploration -> bounded prebound relative MOVE.

Offline-only selection/proposal seam. No Mineflayer commands, native issue,
WAL writes, GPU scheduling, Paper effects or inferred destination arrival.
The Stage23b original PhysicalIssueAdmission remains the only motor issuer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    L1Round,
    Option,
    Selection,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns_with_relative_move,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionProposalReceipt,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, RelayEngineResult
from relay_self.skill import SkillExecution

RELATIVE_CONTROLS = ("forward", "back", "left", "right")
MOVE_PULSE_SECONDS = 0.35
MOVE_SKILLS = frozenset({("MOVE", 1)})


class ResidentL1MoveRefusal(ValueError):
    """Unqualified native source, selection, preset, or owner."""


@dataclass(frozen=True, slots=True)
class PreboundRelativeMove:
    """The complete frozen runtime parameters associated with one L1 number."""

    choice_id: str
    option: Option
    pulse_seconds: float
    preset_ref: str = "stage23b-relative-pulse-v1"

    def __post_init__(self) -> None:
        if (
            self.option.skill_id != "MOVE"
            or self.option.skill_version != 1
            or self.option.target_kind != "RELATIVE"
            or self.option.target_ref not in {
                f"relative:{control}" for control in RELATIVE_CONTROLS
            }
            or self.pulse_seconds != MOVE_PULSE_SECONDS
            or not self.choice_id
        ):
            raise ResidentL1MoveRefusal("unqualified bound MOVE option")


@dataclass(frozen=True, slots=True)
class ResidentL1MoveTurn:
    """One source-scoped CPU Schema and full L1 choice set, not a decision."""

    self_id: str
    initial_probe: MineflayerObservation
    round: L1Round
    prebound_moves: tuple[PreboundRelativeMove, ...]
    candidate_set_sha256: str
    exploration_need_active: bool  # innate Need, never motor permission

    def candidate_for(self, choice_id: str) -> PreboundRelativeMove | None:
        return next(
            (candidate for candidate in self.prebound_moves
             if candidate.choice_id == choice_id),
            None,
        )


@dataclass(frozen=True, slots=True)
class ResidentL1MoveDecision:
    """Validated chosen option, still without Intent commit or Action issuing."""

    status: str
    selection: Selection
    candidate: PreboundRelativeMove | None
    current_probe: MineflayerObservation
    candidate_set_sha256: str


def _canonical_digest(
    self_id: str, probe: MineflayerObservation,
    candidates: tuple[PreboundRelativeMove, ...],
) -> str:
    body = {
        "self_id": self_id,
        "native_session": probe.session_id,
        "native_seq": probe.seq,
        "native_request_id": probe.request_id,
        "native_source": (probe.provenance.source, probe.provenance.reference),
        "candidates": [
            {
                "number": item.choice_id,
                "goal": item.option.goal_id,
                "skill": item.option.skill_id,
                "version": item.option.skill_version,
                "target_kind": item.option.target_kind,
                "target_ref": item.option.target_ref,
                "preset_ref": item.preset_ref,
                "pulse_seconds": item.pulse_seconds,
            }
            for item in candidates
        ],
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_resident_l1_move_turn(
    probe: MineflayerObservation, *,
    self_id: str,
    intent_owner: IntentCommitment,
    capability: PhysicalCapability,
    epoch: int,
) -> ResidentL1MoveTurn:
    """Offer innate exploration as a Goal, not as a Body/World permission.

    Oxygen reserve, hunger, health, nearby threats, World time and sensor
    coverage inform separate Needs/experience. They never mask the MOVE
    options. Relative controls are reference actions, not a reachability
    guarantee. Only the original physical issuer knows the actual Outcome.
    """
    if (
        not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe"
        or not probe.request_id
        or not isinstance(self_id, str)
        or not self_id.strip()
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(capability, PhysicalCapability)
        or type(epoch) is not int
        or epoch < 0
    ):
        raise ResidentL1MoveRefusal("current typed native probe/owner required")
    if (
        capability.capability_ref != "MOVE"
        or capability.version != 1
        or capability.target_kind != "RELATIVE"
        or capability.body_channel != "locomotion"
    ):
        raise ResidentL1MoveRefusal("unqualified physical MOVE catalogue")

    # Exploration is a standing innate Need; L1 may select it or favor an
    # urgent homeostatic Need. Do not use physiology as action permission.
    exploration = True
    references = (
        tuple(
            Target(
                f"relative:{control}", "RELATIVE",
                probe.provenance, probe.session_id, probe.seq,
            )
            for control in RELATIVE_CONTROLS
        )
        if exploration and capability.available else ()
    )
    food = probe.snapshot.food
    percept = WorldPercept(
        scope=ScopeRef(self_id, probe.session_id),
        source=probe.provenance,
        sequence=probe.seq,
        hunger=int(food) if float(food).is_integer() else None,
        fatigue_high=None,  # not measured in the native snapshot
        targets=references,
        exploration_need=exploration,
        oxygen_reserve=probe.snapshot.oxygen_level,
        threat_cue=any(e.name == "zombie" for e in probe.snapshot.nearby_entities),
    )
    frame = cpu_schema_epoch(
        percept, initial_patterns_with_relative_move(),
        allowed_skills=MOVE_SKILLS if capability.available else frozenset(),
        epoch=epoch,
    )
    round_ = assemble_l1_select(frame, intent_owner=intent_owner)
    # Add already fixed motor parameters to the model-facing numbered choices.
    labels = []
    candidates = []
    for (number, option), choice in zip(round_.numbered, round_.request.choices, strict=True):
        if isinstance(option, Option):
            bound = PreboundRelativeMove(number, option, MOVE_PULSE_SECONDS)
            candidates.append(bound)
            label = (
                f"{choice.description} [preset={bound.preset_ref},"
                f" pulse={bound.pulse_seconds:g}s, START]"
            )
            labels.append(BoundedChoice(number, label))
        else:
            labels.append(choice)
    round_ = replace(round_, request=replace(round_.request, choices=tuple(labels)))
    prebound = tuple(candidates)
    return ResidentL1MoveTurn(
        self_id, probe, round_, prebound,
        _canonical_digest(self_id, probe, prebound), exploration,
    )


def resolve_resident_l1_move(
    turn: ResidentL1MoveTurn,
    result: RelayEngineResult,
    *,
    current_probe: MineflayerObservation,
    intent_owner: IntentCommitment,
    capability: PhysicalCapability,
    epoch: int,
) -> ResidentL1MoveDecision:
    """Check selected dependencies on fresh source, never reselect parameters."""
    if (
        not isinstance(turn, ResidentL1MoveTurn)
        or not isinstance(result, RelayEngineResult)
        or not isinstance(current_probe, MineflayerObservation)
        or current_probe.session_id != turn.initial_probe.session_id
        or current_probe.seq <= turn.initial_probe.seq
        or current_probe.request_id == turn.initial_probe.request_id
    ):
        raise ResidentL1MoveRefusal("replayed, absent or foreign second native probe")
    if _canonical_digest(turn.self_id, turn.initial_probe, turn.prebound_moves) != turn.candidate_set_sha256:
        raise ResidentL1MoveRefusal("candidate set differs from frozen original")
    fresh = build_resident_l1_move_turn(
        current_probe, self_id=turn.self_id,
        intent_owner=intent_owner, capability=capability, epoch=epoch,
    )
    chosen = resolve_l1_choice(
        turn.round, result, current_frame=fresh.round.frame,
        intent_owner=intent_owner,
        available_skills=MOVE_SKILLS if capability.available else frozenset(),
    )
    candidate = turn.candidate_for(result.choice_id or "") if chosen.status == "READY" else None
    if chosen.status == "READY" and (
        candidate is None or chosen.option != candidate.option
        or candidate not in turn.prebound_moves
    ):
        raise ResidentL1MoveRefusal("unbound or stale selected physical preset")
    return ResidentL1MoveDecision(
        chosen.status, chosen, candidate, current_probe, turn.candidate_set_sha256,
    )


def propose_resident_l1_move(
    decision: ResidentL1MoveDecision,
    *,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    intent_id: str,
    action_id: str,
    at_ns: int,
    provenance: Provenance,
) -> PhysicalActionProposalReceipt:
    """Join the selected option to original ActionPort; strictly NO ISSUE.

    The original Stage23b issuer must separately check two fresh post-L1
    probes, canonical WAL, physical grants, final stdin and STOP/settling.
    """
    item = decision.candidate
    if (
        decision.status != "READY" or item is None
        or decision.selection.option != item.option
        or decision.selection.world_scope is None
        or decision.selection.world_scope.world_session_id != decision.current_probe.session_id
        or not isinstance(provenance, Provenance)
    ):
        raise ResidentL1MoveRefusal("only current selected MOVE can be proposed")
    probe = decision.current_probe
    binding = PhysicalActionBinding(
        scope=decision.selection.world_scope,
        intent_id=intent_id,
        goal_id=item.option.goal_id,
        skill_id=item.option.skill_id,
        skill_version=item.option.skill_version,
        skill_execution_id=skill_execution.execution_id,
        action_id=action_id,
        capability_ref="MOVE",
        capability_version=1,
        body_channel="locomotion",
        target_kind="RELATIVE",
        target_ref=item.option.target_ref,
        native_seq=probe.seq,
        native_request_id=probe.request_id or "",
        native_source=probe.provenance,
    )
    return propose_bound_physical_action(
        binding,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "RELATIVE", True),
        readback=PhysicalReadback(
            binding.scope, probe.provenance, probe.seq, probe.request_id or "",
            (binding.target_ref,), probe.snapshot.health > 0,
        ),
        intent_owner=intent_owner, skill_execution=skill_execution,
        supervisor=supervisor, at_ns=at_ns, provenance=provenance,
    )
