"""#860 Stage25: verify NEW source-qualified native readback uses restored Preset.

Read-only: builds one Goal-specific operator DEV destination anchored to a
genuine new native probe; a scripted number-only L1 choice shows a usable
restored candidate. This never admits or sends MOVE or resumes any old Intent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerPosition,
)
from relay_self.checkpointed_cognitive_runtime_dev import StagedRecoveredCognition
from relay_self.cognitive_minimal_dev import (
    Option,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import ProviderDecision, RelayEngine
from relay_self.skill_invocation import SkillDefinition
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)


class RestoredPresetRealProbeRefusal(ValueError):
    """Recovered cognition and actual new native source cannot be reconciled."""


@dataclass(frozen=True, slots=True)
class RestoredPresetProbeWitness:
    self_id: str
    old_native_session_id: str
    new_native_session_id: str
    initial_probe_id: str
    current_probe_id: str
    initial_native_seq: int
    current_native_seq: int
    registry_revision: int
    preset_ref: str
    invocation_ref: str
    target_contract_ref: str
    l1_number: str
    choice_status: str
    provider_kind: str = "SCRIPTED_NUMBER_ONLY_DEV_NOT_GEMMA"
    physical_action_issued: bool = False
    native_action_granted: bool = False
    old_intent_resumed: bool = False
    old_target_reused: bool = False


def _reselect_steps(
    restored: StagedRecoveredCognition,
    first: MineflayerObservation,
    *,
    source_self_id: str,
    expected_native_session_id: str,
    definition: SkillDefinition | None = None,
) -> RestoredPresetProbeWitness:
    """Read-only CURRENT->number SELECT->new CURRENT; no effect commands.

    Operator's demonstration target is exactly 1m east of the observed
    position. This is a target *hypothesis* for L1 selection only: terrain
    access and physical reachability have NOT been qualified.
    """
    if (
        not isinstance(restored, StagedRecoveredCognition)
        or type(source_self_id) is not str
        or restored.self_id != source_self_id
        or type(expected_native_session_id) is not str
        or not expected_native_session_id
        or not isinstance(first, MineflayerObservation)
        or first.kind != "probe"
        or not first.request_id
        or not (restored.fresh_worldbody_required
                and not restored.native_session_bound
                and not restored.issue_authorized
                and not restored.semantic.old_skill_resume_authorized
                and not restored.semantic.new_physical_action_issue_authorized)
        or first.session_id != expected_native_session_id
        or first.session_id == restored.semantic.cut.former_native_session_id
        or first.seq < 0
        or first.snapshot.health <= 0
        or first.snapshot.time is None
        or restored.retained.identity.self_id != restored.self_id
        or restored.retained.pattern_registry != restored.semantic.pattern_registry
    ):
        raise RestoredPresetRealProbeRefusal(
            "new original native probes or inert adopted registry missing"
        )
    a = first.snapshot.position
    if definition is None:
        definition = next(
            d for d in initial_skill_definitions() if d.skill_id == "MOVE"
        )
    if definition.skill_id != "MOVE" or definition.version != 1:
        raise RestoredPresetRealProbeRefusal("only bounded MOVE@1 hypothesis accepted")
    scope = ScopeRef(restored.self_id, first.session_id)
    target_ref = f"destination:stage25-{restored.self_id}"
    # A bounded operator-proposed geometric target; NOT a physical permission.
    contract = TargetContract(
        scope=scope,
        goal_id="EXPLORE_WORLD", target_ref=target_ref,
        kind=TargetKind.PLACE, reference_frame=ReferenceFrame.WORLD,
        provenance=first.provenance,
        condition=ArrivalCondition(0.0, 0.6, 1.0),
        bound_seq=first.seq,
        anchor=MineflayerPosition(a.x + 1.0, a.y, a.z),
    )
    original_target = Target(
        target_ref, "DESTINATION", first.provenance, first.session_id,
        first.seq, arrival_contract=contract,
    )
    registry = restored.semantic.pattern_registry
    available = frozenset({("MOVE", 1)})
    definitions = {("MOVE", 1): definition}
    first_frame = cpu_schema_epoch(
        WorldPercept(
            scope, first.provenance, first.seq,
            hunger=int(first.snapshot.food), fatigue_high=False,
            targets=(original_target,), exploration_need=True,
        ), registry, allowed_skills=available, epoch=1,
        skill_definitions=definitions, use_registered_presets=True,
    )
    if len(first_frame.options) != 1:
        raise RestoredPresetRealProbeRefusal(
            "restored learned MOVE Preset not eligible in fresh WorldBody"
        )
    option = first_frame.options[0]
    if option.invocation is None:
        raise RestoredPresetRealProbeRefusal("L1 option missing complete Invocation")
    owner = IntentCommitment()
    round_ = assemble_l1_select(first_frame, intent_owner=owner)
    choice = next(
        (n for n, candidate in round_.numbered
         if isinstance(candidate, Option) and candidate == option),
        None,
    )
    if choice is None:
        raise RestoredPresetRealProbeRefusal("no numbered completed Skill candidate")
    # Separate genuine SystemOne/Gemma qualification is NOT run here.
    scripted = RelayEngine(
        lambda request, *, mode: ProviderDecision.resolved(choice),
    )(round_.request)
    # The caller must obtain the second observation only after the choice.
    refreshed = yield
    if (
        not isinstance(refreshed, MineflayerObservation)
        or refreshed.kind != "probe" or not refreshed.request_id
        or first.request_id == refreshed.request_id
        or first.session_id != refreshed.session_id
        or not first.seq < refreshed.seq
        or refreshed.snapshot.health <= 0 or refreshed.snapshot.time is None
    ):
        raise RestoredPresetRealProbeRefusal("new original native probes invalid")
    b = refreshed.snapshot.position
    if math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) > 0.25:
        raise RestoredPresetRealProbeRefusal("moving target source unstable")
    # The same operator-proposed destination is still admitted as a Goal
    # hypothesis after a second NEW native probe. Use original bound Target
    # provenance, not a forged fresh target precision.
    current_frame = cpu_schema_epoch(
        WorldPercept(
            scope, refreshed.provenance, refreshed.seq,
            hunger=int(refreshed.snapshot.food), fatigue_high=False,
            targets=(original_target,), exploration_need=True,
        ), registry, allowed_skills=available, epoch=2,
        skill_definitions=definitions, use_registered_presets=True,
    )
    result = resolve_l1_choice(
        round_, scripted, current_frame=current_frame,
        intent_owner=owner, available_skills=available,
    )
    if result.status != "READY" or result.option != option:
        raise RestoredPresetRealProbeRefusal(
            "selected Preset stale after new native source readback"
        )
    return RestoredPresetProbeWitness(
        self_id=restored.self_id,
        old_native_session_id=restored.semantic.cut.former_native_session_id,
        new_native_session_id=first.session_id,
        initial_probe_id=first.request_id,
        current_probe_id=refreshed.request_id,
        initial_native_seq=first.seq,
        current_native_seq=refreshed.seq,
        registry_revision=registry.revision,
        preset_ref=option.invocation.parameter_preset_ref or "",
        invocation_ref=option.invocation.invocation_ref,
        target_contract_ref=contract.contract_ref,
        l1_number=choice,
        choice_status=result.status,
    )


def reselect_restored_move_preset(restored, first, refreshed, **kwargs):
    """Offline compatibility helper; live caller uses the ordered async path."""
    steps = _reselect_steps(restored, first, **kwargs)
    next(steps)
    try:
        steps.send(refreshed)
    except StopIteration as done:
        return done.value
    raise RestoredPresetRealProbeRefusal("unexpected selection continuation")


async def reselect_restored_move_preset_live(restored, first, probe, **kwargs):
    """Choose first, then request the new observation and revalidate."""
    steps = _reselect_steps(restored, first, **kwargs)
    next(steps)
    refreshed = await probe()
    try:
        steps.send(refreshed)
    except StopIteration as done:
        return done.value, refreshed
    raise RestoredPresetRealProbeRefusal("unexpected selection continuation")
