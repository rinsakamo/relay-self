"""DEV-only native Mineflayer -> CPU Schema -> L1 -> existing Action executor.

Uses the *existing* controlled Minecraft EAT/FIGHT action path and
ActionSupervisor. Does not create a second issuer or independent scheduler.
The input is a decoded, session-validated MineflayerObservation from the
existing bridge. Caller supplies explicit physical capability knowledge.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.controlled_minecraft_vertical import (
    ControlledScenario,
    ControlledSkill,
    MineflayerScenarioSession,
    ScenarioDecision,
    SkillRunResult,
    execute_decision,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    L1Round,
    MinimalCognitionError,
    Option,
    PatternRegistry,
    SchemaFrame,
    Selection,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import RelayEngine, RelayEngineResult

# This is a one-turn integration for the existing main branch's bounded MVP
# executor, NOT an implementation of unmerged S49's full optional adapter.
L1Callable = Callable[[object], RelayEngineResult]


@dataclass(frozen=True, slots=True)
class WorldStepReceipt:
    """Keep model decision, selected dependencies and actual action evidence distinct."""
    status: str
    selection: Selection
    initial_frame: SchemaFrame
    current_frame: SchemaFrame | None
    l1_result: RelayEngineResult
    l1_elapsed_ns: int
    probe_elapsed_ns: int | None
    run: SkillRunResult | None
    native_eat_consequence_attested: bool | None = None

    @property
    def actual_action_outcomes(self) -> int:
        if self.run is None:
            return 0
        from relay_self.action import ActionState

        return sum(action.state is ActionState.OUTCOME for action in self.run.actions)


def _native_eat_consequence_attested(
    before: MineflayerObservation,
    run: SkillRunResult,
) -> bool:
    """Stronger post-EAT native evidence; does not mutate legacy SkillState.

    Follows #767 semantics: two applied native primitive ACKs, later food
    increase and inventory decrease. This still is NOT an original S49 S16
    durable fence or real-world physical exactly-once proof.
    """
    item_name = run.decision.item_name
    if run.decision.skill is not ControlledSkill.EAT or item_name is None:
        return False
    initial_count = sum(
        item.count for item in before.snapshot.inventory if item.name == item_name
    )
    if initial_count <= 0:
        return False
    applied_effects = {
        msg.effect for msg in run.messages
        if isinstance(msg, MineflayerEffectResult)
        and msg.session_id == before.session_id
        and msg.result == "applied"
        and msg.action_id in {action.action_id for action in run.actions}
    }
    if not {"equip_item", "consume_held"}.issubset(applied_effects):
        return False
    for msg in run.messages:
        if not isinstance(msg, MineflayerObservation):
            continue
        if msg.session_id != before.session_id or msg.seq <= before.seq:
            continue
        after_count = sum(
            item.count for item in msg.snapshot.inventory if item.name == item_name
        )
        if msg.snapshot.food > before.snapshot.food and after_count < initial_count:
            return True
    return False


def native_schema_percept(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    self_id: str,
) -> WorldPercept:
    """Source-qualified native projection; no Minecraft-native threat classifier.

    Edibility, hazard identity and ATTACK physical range are provided by the
    existing *scenario* capability contract, not inferred from the LLM or
    hardcoded into the Schema engine. Physical fatigue is UNKNOWN in the
    current Mineflayer adapter and is not invented.
    """
    if not isinstance(observation, MineflayerObservation):
        raise MinimalCognitionError("native decoder observation required")
    if not isinstance(scenario, ControlledScenario):
        raise MinimalCognitionError("existing ControlledScenario required")
    if not isinstance(self_id, str) or not self_id.strip():
        raise MinimalCognitionError("Self identity required")
    if observation.kind == "death" or observation.snapshot.health <= 0:
        raise MinimalCognitionError("dead WorldBody is not actionable")

    snapshot = observation.snapshot
    hunger = int(snapshot.food) if float(snapshot.food).is_integer() else None
    targets: list[Target] = []
    # Existing adapter sends items and counts, not an is_edible fact. The
    # scenario's explicitly recognized food names are the only valid EAT targets.
    inventory_names = {
        item.name for item in snapshot.inventory
        if item.count > 0 and item.name in scenario.edible_item_names
    }
    for name in sorted(inventory_names)[:8]:
        targets.append(Target(
            f"inventory:{name}", "FOOD", observation.provenance,
            observation.session_id, observation.seq,
        ))

    observed_threats = [
        entity for entity in snapshot.nearby_entities
        if entity.name == "zombie" and entity.name in scenario.hazard_entity_names
    ]
    # A distant threat still motivates DEFEND_SELF, even when ATTACK lacks
    # current physical range. Never offer ATTACK beyond the configured port.
    within_range = [
        entity for entity in observed_threats
        if scenario.fight_max_distance is not None
        and entity.distance <= scenario.fight_max_distance
    ]
    for entity in within_range[:8]:
        targets.append(Target(
            f"entity:{entity.entity_id}", "ZOMBIE", observation.provenance,
            observation.session_id, observation.seq,
        ))

    return WorldPercept(
        scope=ScopeRef(self_id, observation.session_id),
        source=observation.provenance,
        sequence=observation.seq,
        hunger=hunger,
        fatigue_high=None,  # No native fatigue sensor in this adapter.
        targets=tuple(targets),
        threat_cue=bool(observed_threats),
    )


def _rebound_decision(
    option: Option,
    fresh: MineflayerObservation,
    scenario: ControlledScenario,
) -> ScenarioDecision:
    """Bind exactly selected target to existing EAT/FIGHT executor, never reselect."""
    if option.skill_id == "EAT" and option.target_kind == "FOOD":
        prefix = "inventory:"
        if not option.target_ref.startswith(prefix):
            raise MinimalCognitionError("invalid bound FOOD reference")
        name = option.target_ref[len(prefix):]
        if (
            name not in scenario.edible_item_names
            or not any(item.name == name and item.count > 0
                       for item in fresh.snapshot.inventory)
        ):
            raise MinimalCognitionError("food target missing at ActionPort")
        return ScenarioDecision(
            ControlledSkill.EAT, "L1 selected source-grounded hunger Skill",
            item_name=name,
        )
    if option.skill_id == "ATTACK" and option.target_kind == "ZOMBIE":
        prefix = "entity:"
        if not option.target_ref.startswith(prefix):
            raise MinimalCognitionError("invalid bound entity reference")
        try:
            entity_id = int(option.target_ref[len(prefix):])
        except ValueError as exc:
            raise MinimalCognitionError("malformed entity identity") from exc
        if not any(
            entity.entity_id == entity_id
            and entity.name in scenario.hazard_entity_names
            and scenario.fight_max_distance is not None
            and entity.distance <= scenario.fight_max_distance
            for entity in fresh.snapshot.nearby_entities
        ):
            raise MinimalCognitionError("entity target missing/out of port range")
        return ScenarioDecision(
            ControlledSkill.FIGHT, "L1 selected source-grounded defense Skill",
            target_entity_id=entity_id,
        )
    raise MinimalCognitionError("no existing ActionPort adapter for bound Skill")


async def _fresh_probe(
    session: MineflayerScenarioSession,
    initial: MineflayerObservation,
    scenario: ControlledScenario,
) -> MineflayerObservation:
    """One current native observation after L1; bounded, fail closed.

    Does not swallow an unexpected primitive effect receipt that belongs to
    another owner: the caller must coordinate other outstanding actions first.
    """
    await session.send_observe()
    deadline = asyncio.get_running_loop().time() + scenario.evidence_timeout_s
    for _ in range(scenario.max_evidence_messages):
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise MinimalCognitionError("fresh native probe timed out")
        try:
            message = await asyncio.wait_for(session.receive(), timeout=remaining)
        except TimeoutError as exc:
            raise MinimalCognitionError("fresh native probe timed out") from exc
        if message.session_id != initial.session_id:
            raise MinimalCognitionError("World session changed during L1/probe")
        if message.seq <= initial.seq:
            raise MinimalCognitionError("non-monotonic native probe")
        if isinstance(message, MineflayerEffectResult):
            raise MinimalCognitionError("unexpected Action receipt during probe")
        if isinstance(message, (MineflayerConnectionEnd, MineflayerCommandError,
                                MineflayerAdapterErrorMessage)):
            raise MinimalCognitionError("native probe session became unavailable")
        if isinstance(message, MineflayerObservation):
            if message.kind in {"death", "respawn"} or message.snapshot.health <= 0:
                raise MinimalCognitionError("WorldBody life-cycle changed")
            if message.kind == "probe":
                return message
    raise MinimalCognitionError("no qualified probe within bounded event horizon")


async def execute_one_cognitive_world_turn(
    session: MineflayerScenarioSession,
    initial_observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    self_id: str,
    intent_id: str,
    registry: PatternRegistry,
    relay_engine: RelayEngine,
    intent_owner: IntentCommitment,
    supervisor: ActionSupervisor,
    grant_real_world: bool,
    issue_native: bool = False,
    acknowledge_unfenced_dev: bool = False,
    allowed_skills: frozenset[tuple[str, int]] = frozenset({
        ("EAT", 1), ("ATTACK", 1),
    }),
    epoch: int = 1,
    recent_3self: tuple[str, ...] = (),
) -> WorldStepReceipt:
    """Run a single DEV turn; native issuance only via existing execute_decision.

    Never call prepare_existing_owner_action here: that would start a second
    Skill/Action root ahead of the controlled MVP's canonical physical issuer.
    Physical issuance here uses the existing experimental main-branch issuer;
    it does NOT write or restore #767's original S49 durable fence.
    Callers must explicitly acknowledge this DEV-only crash/retry risk.
    The model is called off the event-loop thread, so an independent CPU
    perception owner *can* continue, but this one-shot runner does not itself
    implement a continuous L0/FAST loop or GPU preemption.
    """
    if grant_real_world is not True:
        raise MinimalCognitionError("real World DEV requires explicit grant")
    if type(issue_native) is not bool or type(acknowledge_unfenced_dev) is not bool:
        raise MinimalCognitionError("native issuance flags must be bool")
    if issue_native and not acknowledge_unfenced_dev:
        raise MinimalCognitionError(
            "native issue is UNFENCED_DEV_ONLY; original S49 #767 "
            "pre-ISSUE journal not integrated; explicit risk acknowledgement required"
        )
    if not isinstance(relay_engine, RelayEngine):
        raise MinimalCognitionError("existing RelayEngine required")
    if not isinstance(supervisor, ActionSupervisor):
        raise MinimalCognitionError("existing ActionSupervisor required")
    if not isinstance(intent_owner, IntentCommitment):
        raise MinimalCognitionError("existing IntentCommitment required")
    if supervisor.open_actions:
        raise MinimalCognitionError("existing ActionSupervisor still owns Actions")
    first = native_schema_percept(initial_observation, scenario, self_id=self_id)
    original_frame = cpu_schema_epoch(
        first, registry, epoch=epoch, allowed_skills=allowed_skills,
        hunger_threshold=scenario.food_threshold,
    )
    round_: L1Round = assemble_l1_select(
        original_frame, intent_owner=intent_owner, recent_3self=recent_3self,
    )
    started = time.perf_counter_ns()
    l1_result = await asyncio.to_thread(relay_engine, round_.request)
    l1_elapsed_ns = time.perf_counter_ns() - started

    selected = dict(round_.numbered).get(l1_result.choice_id)
    # Explicit nonphysical options do not require a native Action probe.
    if not isinstance(selected, Option):
        selection = resolve_l1_choice(
            round_, l1_result, current_frame=original_frame,
            intent_owner=intent_owner, available_skills=allowed_skills,
        )
        return WorldStepReceipt(
            selection.status, selection, original_frame,
            None, l1_result, l1_elapsed_ns, None, None,
        )

    # Never infer that L1's now-possibly-stale target still exists.
    probe_started = time.perf_counter_ns()
    current_observation = await _fresh_probe(session, initial_observation, scenario)
    probe_elapsed_ns = time.perf_counter_ns() - probe_started
    current_percept = native_schema_percept(
        current_observation, scenario, self_id=self_id,
    )
    current_frame = cpu_schema_epoch(
        current_percept, registry, epoch=epoch + 1,
        allowed_skills=allowed_skills, hunger_threshold=scenario.food_threshold,
    )
    selection = resolve_l1_choice(
        round_, l1_result, current_frame=current_frame,
        intent_owner=intent_owner, available_skills=allowed_skills,
    )
    if selection.status != "READY" or selection.option is None:
        return WorldStepReceipt(
            selection.status, selection, original_frame,
            current_frame, l1_result, l1_elapsed_ns, probe_elapsed_ns, None,
        )
    if supervisor.open_actions:
        return WorldStepReceipt(
            "DEFER", Selection("DEFER", None, "ActionSupervisor became busy"),
            original_frame, current_frame, l1_result,
            l1_elapsed_ns, probe_elapsed_ns, None,
        )
    # This is a physical-capability check, NOT a second L1 Skill chooser.
    decision = _rebound_decision(selection.option, current_observation, scenario)
    if not issue_native:
        return WorldStepReceipt(
            "READY_NO_ISSUE", selection, original_frame, current_frame,
            l1_result, l1_elapsed_ns, probe_elapsed_ns, None,
        )
    intent_owner.commit(
        intent_id,
        objective=selection.option.goal_id,
        at_ns=time.monotonic_ns(),
        provenance=current_observation.provenance,
    )
    run = await execute_decision(
        session, current_observation, scenario, decision,
        intent_commitment=intent_owner, supervisor=supervisor,
        authorization="cognitive-v0.1-dev-existing-action-boundary",
    )
    return WorldStepReceipt(
        "ACTION_ATTEMPTED", selection, original_frame, current_frame,
        l1_result, l1_elapsed_ns, probe_elapsed_ns, run,
        native_eat_consequence_attested=(
            _native_eat_consequence_attested(current_observation, run)
            if run is not None and decision.skill is ControlledSkill.EAT else None
        ),
    )
