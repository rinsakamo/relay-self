"""L10: preregistered, source-gated World/Body cues -> next-epoch L1 shadow.

This is an offline typed S/L seam. It does not attest original Minecraft
bytes, physical goal success, L1 causal value, M0 energy or Action authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat, _native_threat
from relay_self.contextual_shadow import ShadowContext, ShadowSpecification
from relay_self.experience_bridge import QualifiedEpisode
from relay_self.habit_shadow import ExternalGoalLabel, GoalSourceAdmission, MAX_SAMPLES
from relay_self.l9_world_body_epoch_shadow import (
    WorldBodyEpochShadow,
    WorldBodyEpochRejected,
    observe_s_world_body_epoch_l1,
    verify_original_world_body_present,
)
from relay_self.learning import LearningPreferenceState
from relay_self.learning_epoch import LearningEpochResult, advance_learning_epoch
from relay_self.persistent_cognition import PersistentCognition
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import DecisionEpochResult
from relay_self.epoch_plan import PlannedDecisionEpochResult
from relay_self.self_body import SelfBodyView
from relay_self.self_world import SelfWorldView
from relay_self.world_conditioned_choice import WorldConditionedChoice

_SHA = re.compile(r"[0-9a-f]{64}\Z")
# Fixed S42 physical-distance boundary and independent Minecraft *food* proxy.
# Food is not M0 energy or P1 fatigue. These features cannot authorize Action.
WORLD_NEAR_M = 4.0
BODY_LOW_FOOD_UNITS = 10.0
FEATURE_PAIR = ("body_food_low", "world_zombie_near")
CUE_SCHEMA = "world_body_present_observed"


class WorldBodyCueRejected(ValueError):
    """Source, admitted feature or cross-epoch lineage cannot be joined."""


@dataclass(frozen=True, slots=True)
class WorldBodyCueWitness:
    """One S-owned revision and separately admitted original Present digest."""

    self_id: str
    session_id: str
    native_seq: int
    request_id: str
    source_revision: int
    original_probe_sha256: str
    world_source_ref: str
    body_source_ref: str
    entity_ref: str
    observed_distance_m: float
    observed_food: float
    cue_tags: tuple[str, ...]
    feature_pair: tuple[str, str] = FEATURE_PAIR
    original_physical_source_attested: bool = False
    physical_learning_attested: bool = False
    action_authority: bool = False


@dataclass(frozen=True, slots=True)
class PriorWorldBodyEpisode:
    """Prior positive Present, separate completed S16 Action, separate Goal."""

    native: NativeThreat
    world: SelfWorldView
    body: SelfBodyView
    witness: WorldBodyCueWitness
    outcome: QualifiedEpisode
    goal: ExternalGoalLabel


@dataclass(frozen=True, slots=True)
class L10WorldBodyLearningResult:
    """The existing Memory owner plus current S/L8 read-only comparison."""

    current: WorldBodyCueWitness
    training_witnesses: tuple[WorldBodyCueWitness, ...]
    learning: LearningEpochResult
    observed_s_epoch: WorldBodyEpochShadow
    source_bounded_training: int
    cheap_exact_ref: str | None
    cheap_singleton_ref: str | None
    cheap_global_ref: str | None
    action_issues: int = 0
    native_reads: int = 0
    learning_commits: int = 0
    habit_grants: int = 0
    physical_learning_attested: bool = False
    action_authority: bool = False


def project_admitted_world_body_cues(
    *, native: NativeThreat, world: SelfWorldView, body: SelfBodyView,
    owner_self_id: str, source_revision: int,
    original_probe_sha256: str, admitted_probe_sha256: frozenset[str],
) -> WorldBodyCueWitness:
    """Exact original positive World/Body observations, NEVER inferred defaults.

    S/R/V caller has to qualify original bytes and digest membership. A
    digest-string admission is not independent authenticity.
    """
    if (type(source_revision) is not int or source_revision < 0
            or not isinstance(original_probe_sha256, str)
            or _SHA.fullmatch(original_probe_sha256) is None
            or not isinstance(admitted_probe_sha256, frozenset)
            or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
                   for x in admitted_probe_sha256)
            or original_probe_sha256 not in admitted_probe_sha256):
        raise WorldBodyCueRejected("missing separate S/R/V original Present admission")
    try:
        verify_original_world_body_present(
            native=native, world=world, body=body, owner_self_id=owner_self_id,
        )
        checked = _native_threat(
            native.observation, native.request_id, expected_entity_id=native.entity_id,
        )
    except ValueError as exc:
        raise WorldBodyCueRejected("source-native World/Body Present refused") from exc
    if checked != native:
        raise WorldBodyCueRejected("reported NativeThreat differs from original geometry")
    tags = [CUE_SCHEMA]
    if native.distance_m < WORLD_NEAR_M:
        tags.append(FEATURE_PAIR[1])
    food = body.observed("food")
    if food.value < BODY_LOW_FOOD_UNITS:
        tags.append(FEATURE_PAIR[0])
    return WorldBodyCueWitness(
        self_id=owner_self_id, session_id=native.observation.session_id,
        native_seq=native.observation.seq,
        request_id=native.request_id, source_revision=source_revision,
        original_probe_sha256=original_probe_sha256,
        world_source_ref=world.observation.source_ref,
        body_source_ref=body.observation.source_ref,
        entity_ref=f"entity-{native.entity_id}",
        observed_distance_m=native.distance_m,
        observed_food=food.value, cue_tags=tuple(sorted(tags)),
    )


def evaluate_l10_next_epoch_shadow(
    s_epoch: DecisionEpochResult[object] | PlannedDecisionEpochResult,
    *, native: NativeThreat, world: SelfWorldView, body: SelfBodyView,
    owner: PersistentCognition, retained: LearningPreferenceState,
    current_witness: WorldBodyCueWitness,
    admitted_current_probe_sha256: frozenset[str],
    admitted_prior_probe_sha256: frozenset[str],
    training: tuple[PriorWorldBodyEpisode, ...],
    source_admission: GoalSourceAdmission,
    integration_provenance: Provenance,
    retention_enabled: bool,
) -> L10WorldBodyLearningResult:
    """Retain earlier S16 OUTCOMEs, evaluate later S42 L1 shadow; never select it.

    All training inputs MUST be from different prior sessions and independently
    source/goal qualified by S/R/V. Re-project each prior observation rather
    than trusting a caller-authored tag. Source revision is S supplied, NOT
    native seq, physical WorldTick or an epoch clock.
    """
    if (not isinstance(owner, PersistentCognition)
            or not isinstance(retained, LearningPreferenceState)
            or not isinstance(source_admission, GoalSourceAdmission)
            or not isinstance(integration_provenance, Provenance)
            or type(retention_enabled) is not bool
            or not isinstance(training, tuple)
            or len(training) > MAX_SAMPLES
            or not isinstance(current_witness, WorldBodyCueWitness)):
        raise WorldBodyCueRejected("bounded typed S/L evidence and authority scope required")
    current = project_admitted_world_body_cues(
        native=native, world=world, body=body,
        owner_self_id=owner.identity.self_id,
        source_revision=current_witness.source_revision,
        original_probe_sha256=current_witness.original_probe_sha256,
        admitted_probe_sha256=admitted_current_probe_sha256,
    )
    if current != current_witness:
        raise WorldBodyCueRejected("caller-relabelled current observation feature")
    if isinstance(s_epoch, PlannedDecisionEpochResult):
        decision = s_epoch.decision
    elif isinstance(s_epoch, DecisionEpochResult):
        decision = s_epoch
    else:
        raise WorldBodyCueRejected("original returned S decision result required")
    if not isinstance(decision.cognition_result, WorldConditionedChoice):
        raise WorldBodyCueRejected("S did not return typed World-conditioned choice")
    s_choice = decision.cognition_result
    if (s_choice.session_id != current.session_id
            or s_choice.probe_seq != current.native_seq
            or s_choice.request_id != current.request_id):
        raise WorldBodyCueRejected("S choice does not name current original Present")
    # Validate every historical positive observation AGAINST the original,
    # and bind the independent S16 outcome and external Goal to its S epoch.
    prior_witnesses = []
    episodes = []
    goals = []
    for item in training:
        if not isinstance(item, PriorWorldBodyEpisode):
            raise WorldBodyCueRejected("typed prior observations and terminal required")
        witness = item.witness
        if not isinstance(witness, WorldBodyCueWitness):
            raise WorldBodyCueRejected("prior original witness required")
        reproduced = project_admitted_world_body_cues(
            native=item.native, world=item.world, body=item.body,
            owner_self_id=owner.identity.self_id,
            source_revision=witness.source_revision,
            original_probe_sha256=witness.original_probe_sha256,
            admitted_probe_sha256=admitted_prior_probe_sha256,
        )
        if reproduced != witness:
            raise WorldBodyCueRejected("historic source was relabelled after observation")
        if (witness.session_id == current.session_id
                or witness.source_revision >= current.source_revision
                or not isinstance(item.outcome, QualifiedEpisode)
                or not isinstance(item.goal, ExternalGoalLabel)
                or item.outcome.episode.session_id != witness.session_id
                or item.outcome.episode.world_revision != witness.source_revision
                or item.outcome.episode.cue_tags != witness.cue_tags
                or item.goal.observed_memory_id != item.outcome.episode.memory_id
                or item.outcome.episode.evidence_sha256 == witness.original_probe_sha256
                or item.goal.goal_source_sha256 == witness.original_probe_sha256):
            raise WorldBodyCueRejected("current/future/unbound training source or Goal")
        prior_witnesses.append(witness)
        episodes.append(item.outcome)
        goals.append(item.goal)
    if len({w.session_id for w in prior_witnesses}) != len(prior_witnesses):
        raise WorldBodyCueRejected("historical session replay")
    original_current = ShadowContext(
        session_id=current.session_id,
        source_revision=current.source_revision,
        original_probe_sha256=current.original_probe_sha256,
        cue_tags=current.cue_tags,
        source_provenance=native.observation.provenance,
    )
    learning = advance_learning_epoch(
        owner, current_self_id=owner.identity.self_id,
        current=original_current,
        admitted_current_probe_sha256=admitted_current_probe_sha256,
        specification=ShadowSpecification(
            feature_pair=FEATURE_PAIR, candidate_refs=("MOVE_AWAY", "WAIT"),
        ),
        no_memory_action_ref=s_choice.selection.value,
        previous_goal_labels=(),
        new_episodes=tuple(episodes),
        new_goal_labels=tuple(goals),
        source_admission=source_admission,
        integration_provenance=integration_provenance,
        retention_enabled=retention_enabled,
    )
    # Use L9 to recheck the same S Present and original S choice after L6,
    # but never invoke a second S cognition epoch or its Action issuer.
    observed = observe_s_world_body_epoch_l1(
        s_epoch, native=native, world=world, body=body,
        retained=retained, learning=learning, retention_enabled=retention_enabled,
    )
    return L10WorldBodyLearningResult(
        current=current, training_witnesses=tuple(prior_witnesses),
        learning=learning, observed_s_epoch=observed,
        source_bounded_training=len(prior_witnesses) if retention_enabled else 0,
        cheap_exact_ref=learning.advice.exact_cue_cheap_ref,
        cheap_singleton_ref=learning.advice.singleton_cheap_ref,
        cheap_global_ref=learning.advice.global_cheap_ref,
    )
