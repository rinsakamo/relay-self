"""Stage26 read-only real bounded L1 over a retained Self Preset.

This reuses the original #860 resident llama.cpp one-slot owner and the
accepted-Preset CPU Schema from #923.  A real backend may choose MOVE, DEFER,
ESCALATE_L2, or unresolved; no model answer is converted into an Action grant.
The first native probe precedes the bounded model call; the second is requested
only after the actual backend answer and idle-slot readback.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerPosition,
)
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    StagedRecoveredCognition,
)
from relay_self.cognitive_minimal_dev import (
    L1Round,
    Option,
    PatternRegistry,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill_invocation import SkillDefinition
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)


class Stage26L1Refusal(RuntimeError):
    """Original cognition, new WorldBody source or shared inference not valid."""


@dataclass(frozen=True, slots=True)
class PreparedStage26L1:
    self_id: str
    original_native_session: str
    native_session: str
    first_probe: MineflayerObservation
    restored: StagedRecoveredCognition
    registry_revision: int
    round: L1Round
    original_target: Target
    original_owner: CheckpointedCognitiveOwner
    intent_owner: IntentCommitment
    definition: SkillDefinition
    work_ref: str
    world_epoch: int


@dataclass(frozen=True, slots=True)
class RealGemmaChoiceWitness:
    self_id: str
    former_native_session_id: str
    new_native_session_id: str
    first_probe_id: str
    recheck_probe_id: str
    first_native_seq: int
    recheck_native_seq: int
    world_epoch: int
    registry_revision: int
    selected_number: str | None
    l1_status: str
    l1_reason: str
    available_numbered_choices: tuple[str, ...]
    preset_ref: str
    candidate_invocation_ref: str
    target_contract_ref: str
    backend_ref: str
    inference_work_ref: str
    inference_request_id: str
    backend_slot_idle_after_call: bool
    provider_call_facts: dict[str, object]
    original_http_request_path: str
    original_http_request_sha256: str
    original_http_response_path: str
    original_http_response_sha256: str
    original_http_response_bytes: int
    selection_is_action_permission: bool = False
    issued_native_effect: bool = False
    old_intent_resumed: bool = False
    old_gpu_result_reused: bool = False
    provider_kind: str = "REAL_LLAMA_CPP_BOUNDED_PROVIDER_NOT_SCRIPTED"


def build_stage26_move_round(
    *, self_id: str, registry: PatternRegistry, first: MineflayerObservation,
    definition: SkillDefinition, intent: IntentCommitment,
    stage27i_precision_target: bool = False,
) -> tuple[L1Round, Target]:
    """Build the exact Stage26 model choices using only the CPU."""
    # The DESTINATION remains a hypothetical operator DEMO target, not a
    # terrain-confirmed path. The same new native source is its only anchor.
    scope = ScopeRef(self_id, first.session_id)
    target_ref = f"destination:stage26-{self_id}"
    here = first.snapshot.position
    contract = TargetContract(
        scope=scope, goal_id="EXPLORE_WORLD",
        target_ref=target_ref, kind=TargetKind.PLACE,
        reference_frame=ReferenceFrame.WORLD,
        provenance=first.provenance,
        condition=ArrivalCondition(
            0.0, 0.15 if stage27i_precision_target else 0.6, 1.0,
        ),
        bound_seq=first.seq,
        anchor=MineflayerPosition(
            here.x + (1.5 if stage27i_precision_target else 1.0),
            here.y, here.z,
        ),
    )
    target = Target(
        target_ref, "DESTINATION", first.provenance, first.session_id,
        first.seq, arrival_contract=contract,
    )
    definitions = {("MOVE", 1): definition}
    allowed = frozenset({("MOVE", 1)})
    frame = cpu_schema_epoch(
        WorldPercept(
            scope, first.provenance, first.seq,
            hunger=int(first.snapshot.food), fatigue_high=False,
            targets=(target,), exploration_need=True,
        ), registry, allowed_skills=allowed,
        epoch=first.seq, skill_definitions=definitions,
        use_registered_presets=True,
    )
    if (
        len(frame.options) != 1
        or frame.options[0].invocation is None
        or frame.options[0].invocation.parameter_preset_ref is None
    ):
        raise Stage26L1Refusal("only one fully bound accepted MOVE option required")

    round_ = assemble_l1_select(frame, intent_owner=intent)
    numbered = tuple(n for n, value in round_.numbered if isinstance(value, Option))
    if len(round_.numbered) != 3 or len(numbered) != 1:
        raise Stage26L1Refusal("MOVE, ESCALATE_L2 and DEFER all required")
    if tuple(v for _, v in round_.numbered if isinstance(v, str)) != (
        "ESCALATE_L2", "DEFER",
    ):
        raise Stage26L1Refusal("unqualified L1 option surface")
    return round_, target


def prepare_restored_preset_l1(
    *, self_id: str,
    restored: StagedRecoveredCognition,
    first: MineflayerObservation,
    owner: CheckpointedCognitiveOwner,
    lane: ResidentLlamaInferenceLane,
    definition: SkillDefinition | None = None,
    stage27i_precision_target: bool = False,
) -> PreparedStage26L1:
    """Prepare the complete numbered choices under the *original* owner gate."""
    if (
        type(self_id) is not str
        or not isinstance(restored, StagedRecoveredCognition)
        or restored.self_id != self_id
        or not isinstance(first, MineflayerObservation)
        or first.kind != "probe" or not first.request_id
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or owner.self_id != self_id
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or lane.cognitive_work.owners.get(self_id) is not owner
        or first.session_id == restored.semantic.cut.former_native_session_id
        or first.session_id != owner.native_session_id
        or first.snapshot.health <= 0 or first.snapshot.time is None
        or first.snapshot.food < 0 or first.snapshot.food > 20
        or not restored.fresh_worldbody_required
        or restored.native_session_bound or restored.issue_authorized
        or restored.semantic.old_skill_resume_authorized
        or restored.semantic.new_physical_action_issue_authorized
        or owner.fresh_native_observation_required
        or type(stage27i_precision_target) is not bool
        or restored.retained.identity.self_id != self_id
        or restored.retained.pattern_registry != restored.semantic.pattern_registry
        or owner.retained != restored.retained
        or owner.pattern_registry != restored.semantic.pattern_registry
    ):
        raise Stage26L1Refusal(
            "recovered Self Schema or newly bound native owner source missing"
        )
    try:
        self_epoch, native_id, world_epoch = lane.cognitive_work.current_scope(self_id)
    except (ValueError, RuntimeError, KeyError) as exc:
        raise Stage26L1Refusal("original Self cognitive scope not online") from exc
    if native_id != first.session_id or self_epoch < 1:
        raise Stage26L1Refusal("current native session differs from owned inference epoch")

    if definition is None:
        definition = next(
            d for d in initial_skill_definitions() if d.skill_id == "MOVE"
        )
    if definition.skill_id != "MOVE" or definition.version != 1:
        raise Stage26L1Refusal("only original bounded MOVE@1 candidate allowed")

    intent = IntentCommitment()
    round_, target = build_stage26_move_round(
        self_id=self_id, registry=restored.semantic.pattern_registry,
        first=first, definition=definition, intent=intent,
        stage27i_precision_target=stage27i_precision_target,
    )
    # Source-unique request identity prevents old native epochs presenting an
    # apparently current request with the same schema epoch/choice number.
    request = replace(
        round_.request,
        request_id=f"stage26-l1-{self_id}-{first.session_id}-{first.seq}",
    )
    round_ = replace(round_, request=request)
    return PreparedStage26L1(
        self_id, restored.semantic.cut.former_native_session_id,
        first.session_id, first, restored, round_.frame.registry_revision,
        round_, target, owner, intent, definition,
        f"stage26-{first.session_id}-{first.seq}", world_epoch,
    )


def submit_restored_preset_l1(
    prepared: PreparedStage26L1,
    *, lane: ResidentLlamaInferenceLane,
) -> ResidentInferenceTicket:
    """Model request starts on the same original gated resident GPU owner."""
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or lane.cognitive_work.owners.get(prepared.self_id)
        is not prepared.original_owner
        or prepared.original_owner.pattern_registry
        != prepared.restored.semantic.pattern_registry
    ):
        raise Stage26L1Refusal("foreign/stale inference owner at L1 submission")
    scope = lane.cognitive_work.current_scope(prepared.self_id)
    if scope[1:] != (prepared.native_session, prepared.world_epoch):
        raise Stage26L1Refusal("native or World epoch changed before L1")
    return lane.submit(
        prepared.self_id, work_ref=prepared.work_ref,
        request=prepared.round.request, mode=CognitionMode.BOUNDED,
    )


async def finish_restored_preset_l1(
    prepared: PreparedStage26L1,
    *, ticket: ResidentInferenceTicket,
    lane: ResidentLlamaInferenceLane,
    fresh_probe: Callable[[], Awaitable[MineflayerObservation]],
    result_timeout_s: float = 60.0,
) -> tuple[RealGemmaChoiceWitness, MineflayerObservation]:
    """Real model RETURN + idle /slots -> NEW probe -> current-owner L1 recheck."""
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(ticket, ResidentInferenceTicket)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not callable(fresh_probe)
        or ticket.self_id != prepared.self_id
        or ticket.native_session_id != prepared.native_session
        or ticket.world_epoch != prepared.world_epoch
        or ticket.request_id != prepared.round.request.request_id
        or ticket.work_ref != prepared.work_ref
        or ticket.mode is not CognitionMode.BOUNDED
        or lane.cognitive_work.owners.get(prepared.self_id)
        is not prepared.original_owner
    ):
        raise Stage26L1Refusal("foreign inference ticket or currently owned Self")
    answer = await lane.await_result(ticket, timeout_s=result_timeout_s)
    if not isinstance(answer, ProviderDecision):
        raise Stage26L1Refusal("real bounded provider returned non-choice")
    # The original HTTP response MUST have been fsynced BEFORE backend result.
    # Missing source, missing usage or nonterminal finish always HOLD.
    facts = answer.call_facts
    if (
        facts.prompt_tokens is None or facts.completion_tokens is None
        or facts.total_tokens is None or facts.finish_reason != "stop"
        or facts.total_tokens != facts.prompt_tokens + facts.completion_tokens
    ):
        raise Stage26L1Refusal("unauditable token usage or finish reason")
    raw = lane.provider.stage26_raw_receipt(ticket.request_id)
    # Crucial ordering: MODEL ANSWER must precede a request for fresh WorldBody.
    refreshed = await fresh_probe()
    first = prepared.first_probe
    if (
        not isinstance(refreshed, MineflayerObservation)
        or refreshed.kind != "probe" or not refreshed.request_id
        or refreshed.request_id == first.request_id
        or refreshed.session_id != prepared.native_session
        or not first.seq < refreshed.seq
        or refreshed.snapshot.health <= 0
        or refreshed.snapshot.time is None
        or refreshed.snapshot.food < 0 or refreshed.snapshot.food > 20
    ):
        raise Stage26L1Refusal("post-model fresh native source unavailable")
    here = first.snapshot.position
    now = refreshed.snapshot.position
    if math.dist((here.x, here.y, here.z), (now.x, now.y, now.z)) > 0.25:
        raise Stage26L1Refusal("new WorldBody geometry stale after model answer")
    try:
        # Checking this AFTER the second probe rejects any logout/quarantine or
        # old GPU completion that raced with our actual native observation.
        if lane.result(ticket) != answer:
            raise Stage26L1Refusal("inference result changed after recheck")
    except (ValueError, RuntimeError, KeyError) as exc:
        raise Stage26L1Refusal("late L1 result after owner epoch change") from exc
    if (
        prepared.original_owner.pattern_registry
        != prepared.restored.semantic.pattern_registry
        or prepared.original_owner.native_session_id != refreshed.session_id
        or prepared.original_owner.retained != prepared.restored.retained
    ):
        raise Stage26L1Refusal("original Self knowledge or native binding changed")

    allowed = frozenset({("MOVE", 1)})
    current = cpu_schema_epoch(
        WorldPercept(
            prepared.round.frame.scope, refreshed.provenance,
            refreshed.seq, hunger=int(refreshed.snapshot.food),
            fatigue_high=False, targets=(prepared.original_target,),
            exploration_need=True,
        ), prepared.restored.semantic.pattern_registry,
        allowed_skills=allowed, epoch=refreshed.seq,
        skill_definitions={("MOVE", 1): prepared.definition},
        use_registered_presets=True,
    )
    # This wrapper does not call a model again; the authentic answer has
    # already been accepted by the shared lane and only receives the existing
    # RelayEngineResult + numbered-choice validation contract.
    resolved = RelayEngine(
        lambda request, *, mode: answer,
    )(prepared.round.request)
    selection = resolve_l1_choice(
        prepared.round, resolved, current_frame=current,
        intent_owner=prepared.intent_owner, available_skills=allowed,
    )
    if selection.status not in ("READY", "DEFER", "ESCALATE_L2", "RECONSIDER"):
        raise Stage26L1Refusal("unknown/stale/foreign original numbered L1 choice")
    option = prepared.round.frame.options[0]
    assert option.invocation is not None
    if selection.status == "READY" and selection.option != option:
        raise Stage26L1Refusal("real choice not the current bound Preset")
    witness = RealGemmaChoiceWitness(
        self_id=prepared.self_id,
        former_native_session_id=prepared.original_native_session,
        new_native_session_id=prepared.native_session,
        first_probe_id=first.request_id,
        recheck_probe_id=refreshed.request_id,
        first_native_seq=first.seq,
        recheck_native_seq=refreshed.seq,
        world_epoch=prepared.world_epoch,
        registry_revision=prepared.registry_revision,
        selected_number=resolved.choice_id,
        l1_status=selection.status,
        l1_reason=selection.reason,
        available_numbered_choices=tuple(
            c.choice_id for c in prepared.round.request.choices
        ),
        preset_ref=option.invocation.parameter_preset_ref or "",
        candidate_invocation_ref=option.invocation.invocation_ref,
        target_contract_ref=prepared.original_target.arrival_contract.contract_ref,
        backend_ref=ticket.backend_ref,
        inference_work_ref=ticket.work_ref,
        inference_request_id=ticket.request_id,
        backend_slot_idle_after_call=True,
        provider_call_facts=asdict(answer.call_facts),
        original_http_request_path=raw.request_path,
        original_http_request_sha256=raw.request_sha256,
        original_http_response_path=raw.response_path,
        original_http_response_sha256=raw.response_sha256,
        original_http_response_bytes=raw.response_bytes,
    )
    return witness, refreshed
