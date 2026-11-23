"""Stage28c2c: fresh numbered L1 choice from the ORIGINAL recovered A/B.

CPU work only here. A real online runner must call this AFTER the actual
Stage28c2b Paper/native link, ORIGINAL Owner WorldBody adoption, and a
single-slot llama witness. No restored old choice, model POST, physical
Action, Skill start, Intent commit, Memory mutation, or peer send here.

Recovered PatternRegistry is authoritative; never replace it with new
initial_patterns_with_relative_move merely because L1 should act.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.cognitive_minimal_dev import (
    L1Round,
    Option,
    Predicate,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
)
from relay_self.common_io import ScopeRef
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    ProviderDecision,
    RelayEngine,
    RelayEngineResult,
    project_identity_context,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaSlotIdleReceipt,
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28InertRecovery,
    Stage28NativePaperBodyLink,
    stage28_require_fresh_l1_eligibility,
)
from relay_self.world_resident_lifecycle_dev import Presence, WorldLifetime


class Stage28c2cL1Hold(RuntimeError):
    """Old/stale/fabricated owner, source, GPU choice or target: HOLD."""


# These names are validated physical reference *catalog* kinds only.
# The list neither supplies current Targets nor grants any Action permission.
_KNOWN_SKILLS = frozenset({("EAT", 1), ("ATTACK", 1), ("MOVE", 1)})
_RELATIVE = ("forward", "back", "left", "right")


@dataclass(frozen=True, slots=True)
class Stage28c2cFreshTurn:
    self_id: str
    owner_scope: tuple[int, str, int]
    world_id: str
    paper_session_id: str
    paper_boot_id: str
    native_probe_ref: str
    native_probe_seq: int
    pattern_registry_revision: int
    allowed_skills: frozenset[tuple[str, int]]
    presets: tuple[tuple[str, str], ...]
    original_probe: MineflayerObservation
    round: L1Round
    request: BoundedChoiceRequest
    candidate_set_sha256: str
    request_source_verified: bool = True
    old_decision_reusable: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Stage28c2cL1Result:
    self_id: str
    work_ref: str
    request_id: str
    candidate_set_sha256: str
    backend_ref: str
    native_session_id: str
    world_epoch: int
    self_epoch: int
    choice_id: str | None
    selection_status: str
    selected_goal_id: str | None
    selected_skill_id: str | None
    selected_target_ref: str | None
    selected_preset_ref: str | None
    model_status: str
    prompt_tokens: int | None
    completion_tokens: int | None
    original_owner_same: bool = True
    old_l1_result_reused: bool = False
    action_issued: bool = False
    skill_started: bool = False
    intent_committed: bool = False
    peer_sent: bool = False


def _require_live_original(
    *, bridge: OwnedResidentPhysicalBridge, sid: str,
    boot: Stage28ForkPaperEpoch,
    world: WorldLifetime,
) -> tuple[tuple[int, str, int], MineflayerObservation]:
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.inference_lane is not None:
        raise Stage28c2cL1Hold("CPU preflight requires disconnected GPU")
    return _require_original_sources(bridge=bridge, sid=sid, boot=boot, world=world)


def _require_original_sources(*, bridge, sid, boot, world):
    """Shared identity and observation checks; callers enforce their lane boundary."""
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or sid not in ("A", "B")
        or not isinstance(boot, Stage28ForkPaperEpoch)
        or not isinstance(world, WorldLifetime)
        or bridge.cognitive_work is None
        or not bridge.physical.observation_only
        or bridge.physical.active_action_ids
        or tuple(sorted(bridge.owners)) != ("A", "B")
        or bridge.paper.owned_session_id != boot.paper_session_id
        or world.paper_session_id != boot.paper_session_id
        or world.world_id != boot.source_world_id
        or world.branch_id != boot.fork_branch_id
        or world.epoch != boot.world_epoch
        or bridge.lifecycle.world != world
    ):
        raise Stage28c2cL1Hold("original new WorldBody/observation-only owner required")
    for who in ("A", "B"):
        if (
            bridge.lifecycle.view(who).status is not Presence.ONLINE
            or who not in bridge.last_login_observations
            or who not in bridge.last_login_evidence
            or who not in bridge.sessions
            or bridge.sessions[who].process_returncode is not None
            or bridge.cognitive_work.owners[who] is not bridge.owners[who]
            or bridge.owners[who].cohort is not bridge.cognitive_work
            or bridge.owners[who].supervisor.open_actions
        ):
            raise Stage28c2cL1Hold("original A/B not both live with clean action fence")
        owner = bridge.owners[who]
        probe = bridge.last_login_observations[who]
        evidence = bridge.last_login_evidence[who]
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != evidence.native_session_id
            or probe.request_id != evidence.observation_ref
            or owner.native_session_id != probe.session_id
            or owner.current_worldbody_observation is not probe
            or owner.fresh_native_observation_required
            or owner.retained.identity.self_id != who
            or probe.snapshot.time is None
            or owner.last_observed_tick
            != probe.snapshot.time.day * 24000 + probe.snapshot.time.time_of_day
            or evidence.paper_session_id != world.paper_session_id
            or evidence.world_epoch != world.epoch
            or evidence.action_issue_authorized
            or bridge.physical.current_native_sessions[who] != probe.session_id
            or probe.session_id in boot.historical_native_sessions
        ):
            raise Stage28c2cL1Hold("original Owner did not adopt exact fresh native probe")
    return bridge.cognitive_work.current_scope(sid), bridge.last_login_observations[sid]


def _targets(
    probe: MineflayerObservation,
    owner_patterns,
    allowed_skills: frozenset[tuple[str, int]],
) -> tuple[Target, ...]:
    """Use only currently observed inventory/entities and saved exploration."""
    target_kinds = {
        p.target_kind for p in owner_patterns.patterns
        if (p.skill_id, p.skill_version) in allowed_skills
    }
    targets: list[Target] = []
    native, seq, source = probe.session_id, probe.seq, probe.provenance
    if "FOOD" in target_kinds:
        for item in probe.snapshot.inventory:
            # Stage28b has an original initial EAT/bread primitive, not
            # a general unverified edible-item classifier.
            if item.name == "bread" and item.count > 0:
                targets.append(Target(
                    f"inventory:bread:slot:{item.slot}",
                    "FOOD", source, native, seq,
                ))
    if "ZOMBIE" in target_kinds:
        for entity in probe.snapshot.nearby_entities:
            if entity.name == "zombie":
                targets.append(Target(
                    f"entity:{entity.entity_id}", "ZOMBIE",
                    source, native, seq,
                ))
    if (
        "RELATIVE" in target_kinds
        and any(p.predicate is Predicate.EXPLORE
                for p in owner_patterns.patterns)
    ):
        targets.extend(Target(
            "relative:" + control, "RELATIVE", source, native, seq,
        ) for control in _RELATIVE)
    if len(targets) > 16 or len({t.ref for t in targets}) != len(targets):
        raise Stage28c2cL1Hold("ambiguous or excessive actual native targets")
    return tuple(targets)


def _freeze_hash(
    sid: str, scope: tuple[int, str, int], request: BoundedChoiceRequest,
    boot: Stage28ForkPaperEpoch, probe: MineflayerObservation,
    registry_rev: int, presets: tuple[tuple[str, str], ...],
) -> str:
    source = {
        "self_id": sid,
        "self_scope": scope,
        "paper_session": boot.paper_session_id,
        "paper_boot": boot.paper_boot_id,
        "world_uuid": boot.source_world_id,
        "fork": boot.fork_branch_id,
        "probe_session": probe.session_id,
        "probe_seq": probe.seq,
        "probe_request_id": probe.request_id,
        "probe_provenance": probe.provenance.reference,
        "registry_revision": registry_rev,
        "request_id": request.request_id,
        "choices": [(c.choice_id, c.description) for c in request.choices],
        "presets": presets,
        "context": [(c.key, c.value_json, c.provenance.reference)
                    for c in request.context],
    }
    return hashlib.sha256(json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()


def prepare_fresh_original_l1_turn(
    *, plan: Stage28InertRecovery, bridge: OwnedResidentPhysicalBridge,
    boot: Stage28ForkPaperEpoch, world: WorldLifetime,
    links: tuple[Stage28NativePaperBodyLink, ...],
    idle: LlamaSlotIdleReceipt, self_id: str,
    allowed_skills: frozenset[tuple[str, int]] = frozenset(),
    preset_by_skill: tuple[tuple[str, str], ...] = (),
) -> Stage28c2cFreshTurn:
    """A source-verified CPU L1 turn, never a model inference or Action."""
    if (
        type(allowed_skills) is not frozenset
        or not allowed_skills.issubset(_KNOWN_SKILLS)
        or type(preset_by_skill) is not tuple
        or any(type(k) is not str or type(v) is not str or not k or not v
               for k, v in preset_by_skill)
        or len({key for key, _ in preset_by_skill}) != len(preset_by_skill)
    ):
        raise Stage28c2cL1Hold("known innate Skill and explicit preset catalog required")
    if {f"{skill}@{version}" for skill, version in allowed_skills} != {
        key for key, _ in preset_by_skill
    }:
        raise Stage28c2cL1Hold("each advertised Skill needs exact source-bound Preset")
    scope, probe = _require_live_original(
        bridge=bridge, sid=self_id, boot=boot, world=world,
    )
    login = tuple(bridge.last_login_evidence[sid] for sid in ("A", "B"))
    stage28_require_fresh_l1_eligibility(
        plan, world=world, logins=login,
        idle=idle, boot=boot, links=links,
    )
    owner = bridge.owners[self_id]
    values = probe.snapshot
    targets = _targets(probe, owner.pattern_registry, allowed_skills)
    food = values.food
    percept = WorldPercept(
        scope=ScopeRef(self_id, probe.session_id),
        source=probe.provenance, sequence=probe.seq,
        hunger=int(food) if float(food).is_integer() else None,
        fatigue_high=None,
        targets=targets,
        threat_cue=any(x.name == "zombie" for x in values.nearby_entities),
        exploration_need=any(
            x.predicate is Predicate.EXPLORE
            for x in owner.pattern_registry.patterns
        ),
        oxygen_reserve=values.oxygen_level,
    )
    frame = cpu_schema_epoch(
        percept, owner.pattern_registry, allowed_skills=allowed_skills,
        epoch=scope[0],
    )
    round_ = assemble_l1_select(frame, intent_owner=owner.intent)
    preset_map = dict(preset_by_skill)
    choices = tuple(
        BoundedChoice(
            choice.choice_id,
            choice.description + (
                " [preset=" + preset_map[
                    f"{option.skill_id}@{option.skill_version}"
                ] + ", NOT_AUTHORIZED]"
                if isinstance(option, Option) else ""
            ),
        )
        for choice, (_, option) in zip(
            round_.request.choices, round_.numbered, strict=True,
        )
    )
    source_context = CognitionDatum.from_value(
        "fresh_recovered_worldbody",
        {
            "native_session_id": probe.session_id,
            "native_seq": probe.seq,
            "native_request_id": probe.request_id,
            "paper_session_id": boot.paper_session_id,
            "world_uuid": boot.source_world_id,
            "fork": boot.fork_branch_id,
            "self_epoch": scope[0],
            "health": values.health, "food": values.food,
            "oxygen": values.oxygen_level,
            "position": [
                values.position.x, values.position.y, values.position.z,
            ],
            "observed_targets": [t.ref for t in targets],
            "inventory_count": len(values.inventory),
            "nearby_entity_count": len(values.nearby_entities),
            "nearby_entity_coverage_truncated": (
                values.nearby_entities_coverage.truncated
            ),
            "source_clock": "native-world-day-not-paper-process-tick",
        },
        probe.provenance,
    )
    request = replace(
        round_.request,
        request_id="stage28c2c-" + self_id + "-" + uuid.uuid4().hex,
        choices=choices,
        context=round_.request.context + (source_context,),
        identity_context=project_identity_context(owner.retained.identity),
        think_allowed=False,
    )
    round_ = replace(round_, request=request)
    return Stage28c2cFreshTurn(
        self_id, scope, world.world_id, world.paper_session_id,
        boot.paper_boot_id, probe.request_id or "", probe.seq,
        owner.pattern_registry.revision, allowed_skills,
        preset_by_skill, probe, round_, request,
        _freeze_hash(
            self_id, scope, request, boot, probe,
            owner.pattern_registry.revision, preset_by_skill,
        ),
    )


def validate_fresh_original_l1_result(
    *, bridge: OwnedResidentPhysicalBridge,
    boot: Stage28ForkPaperEpoch,
    turn: Stage28c2cFreshTurn,
    lane: ResidentLlamaInferenceLane,
    ticket: ResidentInferenceTicket,
) -> Stage28c2cL1Result:
    """Use result ONLY from actual registered L1 work, NEVER a saved guess.

    Caller must attach this same lane to original bridge before any call so
    that bridge.logout fences it. Model selection does NOT commit an Intent,
    start a Skill, issue an Action or persist new Memory.
    """
    if (
        not isinstance(turn, Stage28c2cFreshTurn)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or bridge.inference_lane is not lane
        or lane.cognitive_work is not bridge.cognitive_work
        or not isinstance(ticket, ResidentInferenceTicket)
        or ticket.mode is not CognitionMode.BOUNDED
        or ticket.self_id != turn.self_id
        or ticket.request_id != turn.request.request_id
        or ticket.native_session_id != turn.owner_scope[1]
        or ticket.self_epoch != turn.owner_scope[0]
        or ticket.world_epoch != turn.owner_scope[2]
        or ticket.backend_ref != lane.backend_ref
        or turn.old_decision_reusable
        or turn.physical_action_issue_authorized
    ):
        raise Stage28c2cL1Hold("original newly owned L1 ticket required")
    # Recheck the real live Owner after the model returns, not just when
    # sending a prompt. Fail closed if the session/WorldBody has changed.
    if (
        bridge.paper.owned_session_id != boot.paper_session_id
        or bridge.physical.observation_only is not True
        or bridge.physical.active_action_ids
        or bridge.cognitive_work.current_scope(turn.self_id)
        != turn.owner_scope
        or bridge.owners[turn.self_id].current_worldbody_observation
        is not turn.original_probe
        or bridge.last_login_observations[turn.self_id]
        is not turn.original_probe
        or bridge.owners[turn.self_id].pattern_registry.revision
        != turn.pattern_registry_revision
        or _freeze_hash(
            turn.self_id, turn.owner_scope, turn.request, boot,
            turn.original_probe, turn.pattern_registry_revision,
            turn.presets,
        ) != turn.candidate_set_sha256
    ):
        raise Stage28c2cL1Hold("stale/fabricated L1 choice source at readback")
    provider = lane.result(ticket)
    if not isinstance(provider, ProviderDecision):
        raise Stage28c2cL1Hold("actual bounded model did not return numbered choice")
    # One local RelayEngine normalization over ALREADY completed provider
    # output. This does not send an additional model HTTP request.
    decision: RelayEngineResult = RelayEngine(
        lambda request, *, mode: provider
    )(turn.request)
    from relay_self.cognitive_minimal_dev import resolve_l1_choice

    option = resolve_l1_choice(
        turn.round, decision,
        current_frame=turn.round.frame,
        intent_owner=bridge.owners[turn.self_id].intent,
        available_skills=turn.allowed_skills,
    )
    chosen_id = decision.choice_id
    name = next(
        (opt for cid, opt in turn.round.numbered if cid == chosen_id),
        None,
    )
    mapped = (
        dict(turn.presets).get(f"{name.skill_id}@{name.skill_version}")
        if isinstance(name, Option) else None
    )
    return Stage28c2cL1Result(
        turn.self_id, ticket.work_ref, ticket.request_id,
        turn.candidate_set_sha256, ticket.backend_ref,
        ticket.native_session_id, ticket.world_epoch, ticket.self_epoch,
        decision.choice_id, option.status,
        option.option.goal_id if option.option else None,
        option.option.skill_id if option.option else None,
        option.option.target_ref if option.option else None,
        mapped if option.option is not None else None,
        decision.status.value,
        provider.call_facts.prompt_tokens,
        provider.call_facts.completion_tokens,
    )


async def run_one_fresh_original_bounded_choice(
    *, bridge: OwnedResidentPhysicalBridge,
    boot: Stage28ForkPaperEpoch,
    turn: Stage28c2cFreshTurn,
    lane: ResidentLlamaInferenceLane,
    timeout_s: float = 60.0,
) -> Stage28c2cL1Result:
    """One actual owned L1 BOUNDED provider POST, zero physical Actions.

    No retries. On timeout the provider thread may still own GPU resources;
    leave the existing lane in HOLD until its actual future and /slots idle
    have been proven terminal. The bridge must own this same lane for logout.
    """
    if (
        not isinstance(turn, Stage28c2cFreshTurn)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or bridge.inference_lane is not lane
        or lane.cognitive_work is not bridge.cognitive_work
        or not bridge.physical.observation_only
        or bridge.physical.active_action_ids
        or bridge.paper.owned_session_id != boot.paper_session_id
        or turn.paper_session_id != boot.paper_session_id
        or turn.paper_boot_id != boot.paper_boot_id
        or turn.old_decision_reusable
        or turn.physical_action_issue_authorized
        or turn.request.think_allowed
        or turn.original_probe is not (
            bridge.owners[turn.self_id].current_worldbody_observation
        )
        or bridge.cognitive_work.current_scope(turn.self_id)
        != turn.owner_scope
        or _freeze_hash(
            turn.self_id, turn.owner_scope, turn.request, boot,
            turn.original_probe, turn.pattern_registry_revision,
            turn.presets,
        ) != turn.candidate_set_sha256
    ):
        raise Stage28c2cL1Hold("fresh owned bounded L1 pre-submit scope is stale")
    ticket = lane.submit(
        turn.self_id, work_ref="stage28c2c:" + turn.request.request_id,
        request=turn.request, mode=CognitionMode.BOUNDED,
    )
    await lane.await_result(ticket, timeout_s=timeout_s)
    return validate_fresh_original_l1_result(
        bridge=bridge, boot=boot, turn=turn, lane=lane, ticket=ticket,
    )
