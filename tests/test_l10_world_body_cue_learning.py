"""L10: source-bound World/Body food and threat cues vs existing S/L shadows.

All source objects and Goal digests are synthetic offline fixtures: neither
real Minecraft originals nor real learned behavioral improvement.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_experience_bridge as l1
import test_l1_epoch_observer as l8
import test_l1_s_choice_shadow as l7
import test_postmain_s35_event_cognition_gate as s35
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from relay_self.contextual_shadow import ContextualStatus
from relay_self.experience_bridge import qualify_episode
from relay_self.habit_shadow import ExternalGoalLabel, GoalSourceAdmission
from relay_self.l1_s_choice_shadow import SChoiceContrastStatus
from relay_self.l10_world_body_cue_learning import (
    PriorWorldBodyEpisode,
    WorldBodyCueRejected,
    evaluate_l10_next_epoch_shadow,
    project_admitted_world_body_cues,
)
from relay_self.provenance import Provenance
from relay_self.self_body import BodyField, BodyObservation, compose_self_body_view
from relay_self.self_world import (
    WorldEntityObservation,
    WorldObservation,
    compose_self_world_view,
)


def source(*, distance_m: float, food: float, session: str, seq: int):
    """Synthetic NativeThreat + exact typed Present projections (no World IO)."""
    _, frame = s35._source(distance_m=distance_m)
    observed = replace(
        frame, session_id=session, seq=seq, request_id=f"l10-probe-{seq}",
        provenance=Provenance("mineflayer", f"{session}:{seq}"),
        snapshot=replace(frame.snapshot, food=food),
    )
    selected = observed.snapshot.nearby_entities[0]
    native = _native_threat(
        observed, observed.request_id, expected_entity_id=selected.entity_id,
    )
    fields = observed.snapshot
    body_observation = BodyObservation(
        session_id=session, native_seq=seq, request_id=observed.request_id,
        fields=(
            BodyField("position_x", fields.position.x),
            BodyField("position_y", fields.position.y),
            BodyField("position_z", fields.position.z),
            BodyField("health", fields.health),
            BodyField("food", fields.food),
            BodyField("food_saturation", fields.food_saturation),
        ),
        source_provenance=observed.provenance,
    )
    epoch = f"l10-{session}-epoch"
    body = compose_self_body_view(
        session_id=session, epoch_id=epoch, self_id="test-self",
        observation=body_observation,
    )
    coverage = fields.nearby_entities_coverage
    world_observation = WorldObservation(
        observer_id="test-self", session_id=session, native_seq=seq,
        request_id=observed.request_id, provenance=observed.provenance,
        entities=tuple(
            WorldEntityObservation(
                f"entity-{item.entity_id}", item.name,
                (item.position.x, item.position.y, item.position.z),
                item.distance,
            )
            for item in fields.nearby_entities
        ),
        coverage_scope=coverage.source_scope,
        coverage_radius_m=coverage.max_distance,
        coverage_cap=coverage.max_entities,
        coverage_candidates=coverage.candidate_count,
        coverage_truncated=coverage.truncated,
    )
    world = compose_self_world_view(
        self_id="test-self", session_id=session, epoch_id=epoch,
        observation=world_observation, self_body=body,
    )
    return native, world, body


def fixture(*, constant_winner=None, missing_cell=None, contradicted=None):
    initial = l1.identity()
    retained = l7.scenario()[1]  # S-owned rev1 fixed-risk policy
    native, world, body = source(
        distance_m=2.0, food=7.0, session="current-session", seq=400,
    )
    supervisor, s_epoch = l8.run_s_epoch(native, retained)
    current_sha = "a" * 64
    current_admission = frozenset({current_sha})
    current = project_admitted_world_body_cues(
        native=native, world=world, body=body,
        owner_self_id=initial.identity.self_id,
        source_revision=128, original_probe_sha256=current_sha,
        admitted_probe_sha256=current_admission,
    )
    training = []
    prior_sha = []
    action_sha = []
    goal_sha = []
    for low in (False, True):
        for near in (False, True):
            if (low, near) == missing_cell:
                continue
            winning = (
                constant_winner or
                ("WAIT" if low == near else "MOVE_AWAY")
            )
            for action_ref in ("MOVE_AWAY", "WAIT"):
                for repeat in range(2):
                    n = len(training)
                    sid = f"prior-session-{n}"
                    p_native, p_world, p_body = source(
                        distance_m=2.0 if near else 10.0,
                        food=7.0 if low else 17.0,
                        session=sid, seq=20+n,
                    )
                    p_sha = f"{3000+n:064x}"
                    p_witness = project_admitted_world_body_cues(
                        native=p_native, world=p_world, body=p_body,
                        owner_self_id=initial.identity.self_id,
                        source_revision=4, original_probe_sha256=p_sha,
                        admitted_probe_sha256=frozenset({p_sha}),
                    )
                    a_sha, g_sha = f"{1000+n:064x}", f"{2000+n:064x}"
                    action, outcome = l1.terminal(
                        action_id=f"prior-action-{n}", session=sid,
                        action_ref=action_ref,
                    )
                    episode = qualify_episode(
                        action, outcome, world_revision=4,
                        evidence_sha256=a_sha, cue_tags=p_witness.cue_tags,
                    )
                    goal_reached = action_ref == winning
                    if contradicted == (low, near) and repeat == 1:
                        goal_reached = not goal_reached
                    goal = ExternalGoalLabel(
                        episode.episode.memory_id, g_sha, goal_reached,
                        Provenance("synthetic-goal-only", f"goal-{n}"),
                    )
                    training.append(PriorWorldBodyEpisode(
                        p_native, p_world, p_body, p_witness, episode, goal,
                    ))
                    prior_sha.append(p_sha)
                    action_sha.append(a_sha)
                    goal_sha.append(g_sha)
    args = {
        "native": native, "world": world, "body": body,
        "owner": initial, "retained": retained,
        "current_witness": current,
        "admitted_current_probe_sha256": current_admission,
        "admitted_prior_probe_sha256": frozenset(prior_sha),
        "training": tuple(training),
        "source_admission": GoalSourceAdmission(
            frozenset(action_sha), frozenset(goal_sha),
        ),
        "integration_provenance": Provenance("synthetic", "l10-shadow"),
        "retention_enabled": True,
    }
    return args, s_epoch, supervisor


def test_l10_same_present_changes_l1_candidate_only_as_cheap_equivalent():
    args, s_epoch, supervisor = fixture()
    previous_clock = supervisor.last_at_ns
    initial = args["owner"]
    on = evaluate_l10_next_epoch_shadow(s_epoch, **args)
    off = evaluate_l10_next_epoch_shadow(
        s_epoch, **{**args, "retention_enabled": False},
    )
    assert args["owner"] is initial and initial.memories == ()
    assert supervisor.last_at_ns == previous_clock and supervisor.open_actions == ()
    assert on.current.cue_tags == (
        "body_food_low", "world_body_present_observed", "world_zombie_near",
    )
    assert on.source_bounded_training == 16
    assert len(on.training_witnesses) == len(on.learning.cognition.memories) == 16
    assert on.learning.candidate_action_ref == "WAIT"
    assert on.learning.advice.status is ContextualStatus.CHEAP_EQUIVALENT
    assert on.learning.candidate_origin == "cheap_memory_rule"
    assert on.cheap_exact_ref == "WAIT"  # strongest cheap baseline matches
    assert on.observed_s_epoch.original_s_l8.comparison.status is SChoiceContrastStatus.CHEAP_DIFFERS
    assert on.observed_s_epoch.original_s_l8.comparison.s_choice.value == "MOVE_AWAY"
    assert on.observed_s_epoch.original_s_l8.comparison.l1_shadow_ref == "WAIT"
    assert on.observed_s_epoch.original_s_l8.comparison.s_choice_kept
    assert off.learning.candidate_action_ref == "MOVE_AWAY"
    assert off.learning.advice.status is ContextualStatus.NO_GOAL_DATA
    assert off.observed_s_epoch.original_s_l8.comparison.status is SChoiceContrastStatus.WITHHELD
    assert off.source_bounded_training == 0 and not off.learning.cognition.memories
    assert all(not w.original_physical_source_attested for w in on.training_witnesses)
    assert on.action_issues == on.native_reads == on.learning_commits == on.habit_grants == 0
    assert not on.action_authority and not on.physical_learning_attested
    assert not on.learning.action_authority
    assert not on.learning.advice.memory_causal_benefit_established


@pytest.mark.parametrize(("low", "near", "expected"), [
    (True, True, ("body_food_low", "world_body_present_observed", "world_zombie_near")),
    (True, False, ("body_food_low", "world_body_present_observed")),
    (False, True, ("world_body_present_observed", "world_zombie_near")),
    (False, False, ("world_body_present_observed",)),
])
def test_l10_features_are_only_observed_from_current_typed_present(low, near, expected):
    n, w, b = source(
        distance_m=2.0 if near else 10.0,
        food=7.0 if low else 17.0,
        session="new-current", seq=51,
    )
    witness = project_admitted_world_body_cues(
        native=n, world=w, body=b, owner_self_id="test-self",
        source_revision=18, original_probe_sha256="d"*64,
        admitted_probe_sha256=frozenset({"d"*64}),
    )
    assert witness.cue_tags == expected
    assert not witness.physical_learning_attested
    assert not witness.action_authority


@pytest.mark.parametrize(("fault", "expected"), [
    ("no_current_sha", WorldBodyCueRejected),
    ("no_prior_sha", WorldBodyCueRejected),
    ("changed_current_tags", WorldBodyCueRejected),
    ("changed_prior_tags", WorldBodyCueRejected),
    ("changed_prior_food", WorldBodyCueRejected),
    ("changed_prior_world_distance", WorldBodyCueRejected),
    ("future_revision", WorldBodyCueRejected),
    ("same_session", WorldBodyCueRejected),
    ("changed_episode_tags", WorldBodyCueRejected),
    ("changed_episode_revision", WorldBodyCueRejected),
    ("unknown_outcome", ValueError),
    ("missing_goal_admission", ValueError),
    ("missing_action_admission", ValueError),
    ("wrong_goal_memory_id", WorldBodyCueRejected),
    ("source_action_sha_reuse", WorldBodyCueRejected),
    ("retention_not_bool", WorldBodyCueRejected),
    ("no_completed_s_choice", WorldBodyCueRejected),
    ("changed_s_choice", ValueError),
])
def test_l10_rejects_foreign_stale_relabelled_or_unadmitted_training(fault, expected):
    args, s_epoch, _ = fixture()
    item = args["training"][0]
    changed = item
    if fault == "no_current_sha":
        args["admitted_current_probe_sha256"] = frozenset()
    elif fault == "no_prior_sha":
        args["admitted_prior_probe_sha256"] = frozenset()
    elif fault == "changed_current_tags":
        args["current_witness"] = replace(
            args["current_witness"], cue_tags=("forged",),
        )
    elif fault == "changed_prior_tags":
        changed = replace(item, witness=replace(item.witness, cue_tags=("forged",)))
    elif fault == "changed_prior_food":
        fields = tuple(
            replace(f, value=18.0) if f.key == "food" else f
            for f in item.body.observation.fields
        )
        new_body = replace(item.body, observation=replace(
            item.body.observation, fields=fields,
        ))
        changed = replace(item, body=new_body, world=replace(
            item.world, self_body=new_body,
        ))
    elif fault == "changed_prior_world_distance":
        obs = item.world.observation
        entities = (
            replace(obs.entities[0], distance_m=obs.entities[0].distance_m + 1),
        )
        changed = replace(item, world=replace(item.world, observation=replace(
            obs, entities=entities,
        )))
    elif fault == "future_revision":
        changed = replace(item, witness=replace(
            item.witness, source_revision=128,
        ))
    elif fault == "same_session":
        changed = replace(item, witness=replace(
            item.witness, session_id="current-session",
        ))
    elif fault == "changed_episode_tags":
        changed = replace(item, outcome=replace(item.outcome, episode=replace(
            item.outcome.episode, cue_tags=("forged",),
        )))
    elif fault == "changed_episode_revision":
        changed = replace(item, outcome=replace(item.outcome, episode=replace(
            item.outcome.episode, world_revision=10,
        )))
    elif fault == "unknown_outcome":
        from relay_self.action_outcome import ActionOutcomeDisposition
        changed = replace(item, outcome=replace(item.outcome, episode=replace(
            item.outcome.episode, disposition=ActionOutcomeDisposition.UNKNOWN,
        )))
    elif fault == "missing_goal_admission":
        args["source_admission"] = replace(
            args["source_admission"], admitted_goal_sha256=frozenset(),
        )
    elif fault == "missing_action_admission":
        args["source_admission"] = replace(
            args["source_admission"], admitted_action_sha256=frozenset(),
        )
    elif fault == "wrong_goal_memory_id":
        changed = replace(item, goal=replace(
            item.goal, observed_memory_id="l1:foreign",
        ))
    elif fault == "source_action_sha_reuse":
        changed = replace(item, witness=replace(
            item.witness,
            original_probe_sha256=item.outcome.episode.evidence_sha256,
        ))
    elif fault == "retention_not_bool":
        args["retention_enabled"] = "true"
    elif fault == "no_completed_s_choice":
        s_epoch = replace(s_epoch, cognition_result=None)
    elif fault == "changed_s_choice":
        from relay_self.world_conditioned_choice import WorldChoiceKind
        s_epoch = replace(
            s_epoch, cognition_result=replace(
                s_epoch.cognition_result, selection=WorldChoiceKind.WAIT,
            ),
        )
    args["training"] = (changed, *args["training"][1:])
    with pytest.raises(expected):
        evaluate_l10_next_epoch_shadow(s_epoch, **args)


def test_l10_missing_quadrant_or_conflicting_goal_abstains():
    for kw in ({"missing_cell": (False, False)}, {"contradicted": (True, True)}):
        args, epoch, _ = fixture(**kw)
        result = evaluate_l10_next_epoch_shadow(epoch, **args)
        assert result.learning.advice.status is ContextualStatus.INSUFFICIENT
        assert result.learning.candidate_action_ref == "MOVE_AWAY"
        assert not result.observed_s_epoch.original_s_l8.comparison.candidate_differs


def test_l10_cheap_global_control_explains_winner_and_no_claimed_gain():
    args, epoch, _ = fixture(constant_winner="WAIT")
    result = evaluate_l10_next_epoch_shadow(epoch, **args)
    assert result.learning.candidate_action_ref == "WAIT"
    assert result.learning.advice.status is ContextualStatus.CHEAP_EQUIVALENT
    assert result.cheap_global_ref == "WAIT"
    assert not result.learning.advice.goal_improvement_attested
    assert result.learning.learning_updates == result.learning.habit_grants == 0
