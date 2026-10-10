"""I4 offline: source-issued *simulator* Action outcome after real S11 selection.

The inherited B15 sample stream is unchanged. Evaluating a chosen policy
causes an extra B11 CurrentWorld.act() terminal test-world observation; those
new receipts are NEVER released to, nor learned by, the B15 training stream.
The scope is NOT S15/S16 physical Minecraft or production L0/L1 authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
)
from experiments.ac_b_b15_delayed_noise import DelayedEpisode, MatchedPolicies

MANIFEST_PATH = Path(__file__).with_name("ac_integration_i4_manifest.json")
FROZEN_DIGEST = "7d84969b7cd6739f62524edef32452d7c112336f1289d6df9243bdc9a44e1cf4"
PHASES = (0, 1, 2)
CHECKPOINTS = (0, 9)
ARMS = ("HABIT", "CHEAP_TAG")


class I4UnqualifiedTrial(ValueError):
    """Refuse an ineligible or replayed TEST SIMULATOR evaluation Action."""


@dataclass(frozen=True, slots=True)
class SimulatorTrialPermit:
    """Explicit local fixture permission; forgeable, NOT product Action authority."""

    trial_id: str
    source_session: str
    source_revision: int
    source_world_identity: int
    phase: int
    tick: int
    a: int
    b: int
    arm: str
    owner_revision: int
    selected_action: int | None
    granted: bool


@dataclass(frozen=True, slots=True)
class ClosedSimulatorTrial:
    trial_id: str
    phase: int
    tick: int
    a: int
    b: int
    arm: str
    source_session: str
    source_revision: int
    owner_revision: int
    selected_action: int | None
    source_observation: ObservedOutcome | None
    status: str
    success: bool
    released_to_training: bool = False
    physical_minecraft_attested: bool = False
    action_supervisor_authorized: bool = False
    production_habit_committed: bool = False


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise I4UnqualifiedTrial("duplicate JSON manifest key")
        obj[key] = value
    return obj


def freeze_readback() -> dict[str, object]:
    try:
        m = json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                I4UnqualifiedTrial("nonfinite manifest JSON")
            ),
        )
        canonical = json.dumps(
            m, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (OSError, TypeError, ValueError) as exc:
        raise I4UnqualifiedTrial("unqualified manifest source") from exc
    if hashlib.sha256(canonical).hexdigest() != FROZEN_DIGEST:
        raise I4UnqualifiedTrial("frozen I4 manifest digest mismatch")
    return m


def _chosen(policies: MatchedPolicies, a: int, b: int, trial: str, arm: str):
    habit, cheap = policies.decide(a, b, trial)
    return habit if arm == "HABIT" else cheap


def mint_fixture_permit(
    world: CurrentWorld,
    policies: MatchedPolicies,
    *,
    phase: int,
    tick: int,
    a: int,
    b: int,
    arm: str,
) -> SimulatorTrialPermit:
    """Test caller prepares exactly one explicit, local, non-production trial."""
    if (
        not isinstance(world, CurrentWorld)
        or not isinstance(policies, MatchedPolicies)
        or phase not in PHASES
        or tick not in CHECKPOINTS
        or (a, b) not in CONTEXTS
        or arm not in ARMS
    ):
        raise I4UnqualifiedTrial("test trial outside frozen scope")
    token = f"i4:{phase}:{tick}:{a}:{b}:{arm}"
    action = _chosen(policies, a, b, token, arm)
    return SimulatorTrialPermit(
        trial_id=token,
        source_session=world.session,
        source_revision=world.revision,
        source_world_identity=id(world),
        phase=phase,
        tick=tick,
        a=a,
        b=b,
        arm=arm,
        owner_revision=policies.owner.revision,
        selected_action=action,
        granted=True,
    )


def run_scoped_simulator_action(
    world: CurrentWorld,
    policies: MatchedPolicies,
    permit: SimulatorTrialPermit | None,
    spent: set[str],
) -> ClosedSimulatorTrial:
    """One actual source-registered simulator act(); at most once per permit.

    This does NOT use S15 issue/authorization or B11's hidden scoring oracle.
    Caller manages an ephemeral local permit/spend set for tests only.
    """
    if (
        not isinstance(world, CurrentWorld)
        or not isinstance(policies, MatchedPolicies)
        or not isinstance(permit, SimulatorTrialPermit)
        or type(spent) is not set
        or any(type(x) is not str for x in spent)
        or permit.granted is not True
        or type(permit.trial_id) is not str
        or not permit.trial_id
        or permit.trial_id in spent
        or permit.arm not in ARMS
        or type(permit.phase) is not int
        or permit.phase not in PHASES
        or type(permit.tick) is not int
        or permit.tick not in CHECKPOINTS
        or type(permit.a) is not int
        or type(permit.b) is not int
        or (permit.a, permit.b) not in CONTEXTS
        or type(permit.source_revision) is not int
        or type(permit.source_world_identity) is not int
        or type(permit.owner_revision) is not int
        or permit.source_session != "b11-sim-world"
        or permit.source_session != world.session
        or permit.source_revision != world.revision
        or permit.source_world_identity != id(world)
        or permit.owner_revision != policies.owner.revision
        or permit.trial_id
        != f"i4:{permit.phase}:{permit.tick}:{permit.a}:{permit.b}:{permit.arm}"
    ):
        raise I4UnqualifiedTrial("trial not admitted by exact test source/owner")
    selected = _chosen(
        policies, permit.a, permit.b, permit.trial_id, permit.arm,
    )
    if (
        type(permit.selected_action) is not type(selected)
        or permit.selected_action != selected
        or (selected is not None and (type(selected) is not int or selected not in (0, 1)))
    ):
        raise I4UnqualifiedTrial("candidate not exact source-qualified current choice")
    if selected is None:
        spent.add(permit.trial_id)
        return ClosedSimulatorTrial(
            trial_id=permit.trial_id, phase=permit.phase, tick=permit.tick,
            a=permit.a, b=permit.b, arm=permit.arm,
            source_session=world.session, source_revision=world.revision,
            owner_revision=policies.owner.revision,
            selected_action=None, source_observation=None,
            status="ABSTAIN_NO_ACTION", success=False,
        )
    before_actions = world.actions_executed
    observation = world.act(permit.a, permit.b, selected)
    if (
        not isinstance(observation, ObservedOutcome)
        or not world.observed(observation)
        or observation.kind != "OBSERVED_ACTION"
        or observation.session != permit.source_session
        or observation.revision != permit.source_revision
        or observation.a != permit.a
        or observation.b != permit.b
        or observation.action != selected
        or type(observation.success) is not bool
        or world.actions_executed != before_actions + 1
    ):
        raise I4UnqualifiedTrial("missing or forged World terminal simulator receipt")
    spent.add(permit.trial_id)
    return ClosedSimulatorTrial(
        trial_id=permit.trial_id, phase=permit.phase, tick=permit.tick,
        a=permit.a, b=permit.b, arm=permit.arm,
        source_session=world.session, source_revision=world.revision,
        owner_revision=policies.owner.revision,
        selected_action=selected, source_observation=observation,
        status="SIMULATOR_WORLD_TERMINAL_OBSERVED",
        success=observation.success,
    )


def _checkpoint(
    engine: DelayedEpisode,
    phase: int,
    tick: int,
    spent: set[str],
) -> tuple[ClosedSimulatorTrial, ...]:
    before_published = tuple(engine.published)
    before_pending = tuple(engine.pending)
    before_commits = engine.policies.native_s10_commits
    before_grants = engine.policies.independent_s11_grants
    before_owner = engine.policies.owner
    before_tags = tuple(sorted(engine.policies.tag.items()))
    trials: list[ClosedSimulatorTrial] = []
    for a, b in CONTEXTS:
        for arm in ARMS:
            permit = mint_fixture_permit(
                engine.world, engine.policies,
                phase=phase, tick=tick, a=a, b=b, arm=arm,
            )
            trials.append(
                run_scoped_simulator_action(
                    engine.world, engine.policies, permit, spent,
                )
            )
    if (
        tuple(engine.published) != before_published
        or tuple(engine.pending) != before_pending
        or engine.policies.native_s10_commits != before_commits
        or engine.policies.independent_s11_grants != before_grants
        or engine.policies.owner is not before_owner
        or tuple(sorted(engine.policies.tag.items())) != before_tags
    ):
        raise I4UnqualifiedTrial("evaluation receipt leaked into B15 learning")
    return tuple(trials)


def run_i4_simulator_closure() -> dict[str, object]:
    """Caller-explicit three-phase source-matched, actual simulator Action trial."""
    manifest = freeze_readback()
    if (
        manifest["base_b15"] != "68f23eb7b51cf761c6f8eccc575fc2749a55755c"
        or manifest["owner_issue"] != 511
        or manifest["physical_minecraft"] is not False
        or manifest["production_go"] is not False
        or manifest["eval_receipts_feed_training"] is not False
    ):
        raise I4UnqualifiedTrial("wrong frozen I4 scope")
    world = CurrentWorld()
    prior: MatchedPolicies | None = None
    last_training_reports: dict[tuple[int, int, int], bool] | None = None
    all_trials: list[ClosedSimulatorTrial] = []
    spent: set[str] = set()
    phase_stats: list[dict[str, object]] = []
    for phase in PHASES:
        if phase == 1:
            world.change_rule(announce=False)
        engine = DelayedEpisode(world, phase, prior, last_training_reports)
        phase_trials: list[ClosedSimulatorTrial] = []
        first_action_count = world.actions_executed
        for tick in range(10):
            if tick < 8:
                engine.issue_at(tick)
            engine.release_at(tick)
            if tick in CHECKPOINTS:
                phase_trials.extend(_checkpoint(engine, phase, tick, spent))
        if (
            engine.command_count != 8
            or engine.delivered_count != 8
            or len(engine.published) != 8
            or engine.pending
            or world.revision != 0
        ):
            raise I4UnqualifiedTrial("B15 training source schedule was altered")
        issued = sum(x.source_observation is not None for x in phase_trials)
        if world.actions_executed - first_action_count != 8 + issued:
            raise I4UnqualifiedTrial("simulator command count does not close")
        for trial in phase_trials:
            if trial.source_observation is not None and (
                not world.observed(trial.source_observation)
            ):
                raise I4UnqualifiedTrial("returned evaluation source receipt lost")
        phase_stats.append(
            {
                "phase": phase,
                "source_training_actions": engine.command_count,
                "source_training_receipts": engine.delivered_count,
                "followup_actions": issued,
                "habit_followup_actions": sum(
                    x.arm == "HABIT" and x.source_observation is not None
                    for x in phase_trials
                ),
                "tag_followup_actions": sum(
                    x.arm == "CHEAP_TAG" and x.source_observation is not None
                    for x in phase_trials
                ),
                "habit_world_success": sum(
                    x.arm == "HABIT" and x.success for x in phase_trials
                ),
                "tag_world_success": sum(
                    x.arm == "CHEAP_TAG" and x.success for x in phase_trials
                ),
                "contradiction_tick": engine.alarm_tick,
                "evaluation_released_to_training": False,
            }
        )
        all_trials.extend(phase_trials)
        last_training_reports = engine.delivered_index()
        prior = engine.policies

    total_eval = sum(x.source_observation is not None for x in all_trials)
    habit_count = sum(
        x.arm == "HABIT" and x.source_observation is not None for x in all_trials
    )
    tag_count = sum(
        x.arm == "CHEAP_TAG" and x.source_observation is not None for x in all_trials
    )
    habit_success = sum(x.arm == "HABIT" and x.success for x in all_trials)
    tag_success = sum(x.arm == "CHEAP_TAG" and x.success for x in all_trials)
    if (
        world.actions_executed != 62
        or total_eval != 38
        or (habit_count, tag_count) != (19, 19)
        or (habit_success, tag_success) != (14, 14)
        or tuple(x["followup_actions"] for x in phase_stats) != (8, 16, 14)
        or tuple(x["habit_world_success"] for x in phase_stats) != (4, 4, 6)
        or any(x.selected_action != y.selected_action or x.success != y.success
               for x, y in zip(all_trials[::2], all_trials[1::2]))
    ):
        raise I4UnqualifiedTrial("predeclared action/World comparator Grand Null failed")
    return {
        "classification": "I4_SIMULATOR_L1_ACTION_OUTCOME_CLOSED_CHEAP_PARITY",
        "source_session": world.session,
        "source_revision": world.revision,
        "shared_training_world_actions": 24,
        "policy_chosen_world_actions": total_eval,
        "total_actual_simulator_world_actions": world.actions_executed,
        "per_arm_world_actions": (habit_count, tag_count),
        "per_arm_success": (habit_success, tag_success),
        "phase_reports": tuple(phase_stats),
        "trials": tuple(all_trials),
        "source_is_physical_minecraft": False,
        "action_supervisor_issued": False,
        "production_habit_owner": False,
        "actual_l2": False,
        "measured_resource_advantage": False,
        "production_go": False,
    }
