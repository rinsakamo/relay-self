"""L4 prospective matched cheap-baseline/transfer review, NEVER science admission.

The caller must independently verify physical source receipts, goal provenance,
pre-registration and work-unit calibration. A passed dataclass is NOT a signature.
There is no Action/Habit authority, World control, or autonomous learning here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from relay_self.experience_bridge import ReuseQuery, ReuseStatus, retrieve_experience
from relay_self.habit_shadow import ExternalGoalLabel
from relay_self.persistent_cognition import PersistentCognition

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_KEY = re.compile(r"[A-Za-z0-9_.:/-]+\Z")
_MAX_PAIRS = 24
_MAX_TRAIN = 48


class MatchedEvidenceRejected(ValueError):
    """Fail closed on dishonest/replayed/mismatched experimental inputs."""


class TrialArm(str, Enum):
    RETAINED = "retained_memory"
    CHEAP = "cheap_exact_cue"


class LearningReviewStatus(str, Enum):
    NO_MATCHED_HOLDOUT = "no_matched_holdout"
    NO_GOAL_SOURCE = "no_goal_source"
    UNVERIFIED = "unverified_external_receipts"
    NON_MATCHED = "non_matched_world_or_task"
    NO_TRANSFER = "no_independent_transfer"
    CHEAP_NULL_EQUAL = "cheap_null_equal"
    CHEAP_DOMINATES = "cheap_dominates"
    TRADEOFF_UNRESOLVED = "unpriced_goal_cost_tradeoff"
    REVIEW_LIFT_ONLY = "prospective_lift_requires_independent_v"


def _sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _key(value: object) -> bool:
    return isinstance(value, str) and _KEY.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class ExternalTrialAdmission:
    """S/R/V-owned original-byte digest admission supplied from outside L."""

    action_sha256: frozenset[str]
    goal_sha256: frozenset[str]
    decision_sha256: frozenset[str]
    cost_sha256: frozenset[str]
    plan_sha256: frozenset[str]

    def __post_init__(self) -> None:
        for name in (
            "action_sha256", "goal_sha256", "decision_sha256",
            "cost_sha256", "plan_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, frozenset) or any(not _sha(x) for x in value):
                raise MatchedEvidenceRejected("original S/R/V digest admission required")


@dataclass(frozen=True, slots=True)
class ProspectiveTrial:
    pair_id: str
    arm: TrialArm
    session_id: str
    source_head: str
    initial_world_sha256: str
    task_goal_spec_sha256: str
    candidate_set_sha256: str
    cue_key: str
    plan_sha256: str
    decision_sha256: str
    action_sha256: str
    goal_sha256: str
    cost_sha256: str
    goal_reached: bool
    measured_work_units: int
    memory_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("pair_id", "session_id", "cue_key"):
            if not _key(getattr(self, name)):
                raise MatchedEvidenceRejected(f"invalid {name}")
        if (
            not isinstance(self.arm, TrialArm)
            or not isinstance(self.source_head, str)
            or _HEAD.fullmatch(self.source_head) is None
        ):
            raise MatchedEvidenceRejected("typed arm and pinned exact source HEAD")
        for name in (
            "initial_world_sha256", "task_goal_spec_sha256",
            "candidate_set_sha256", "plan_sha256", "decision_sha256",
            "action_sha256", "goal_sha256", "cost_sha256",
        ):
            if not _sha(getattr(self, name)):
                raise MatchedEvidenceRejected(f"source digest invalid: {name}")
        if (
            type(self.goal_reached) is not bool
            or type(self.measured_work_units) is not int
            or not 0 <= self.measured_work_units <= 1_000_000
        ):
            raise MatchedEvidenceRejected("typed outcome and bounded work required")
        if self.arm is TrialArm.RETAINED:
            if (
                not isinstance(self.memory_id, str)
                or not self.memory_id.startswith("l1:")
            ):
                raise MatchedEvidenceRejected("retained arm needs original prior L1 Memory")
        elif self.memory_id is not None:
            raise MatchedEvidenceRejected("cheap arm must not access retained Memory")


@dataclass(frozen=True, slots=True)
class MatchedReview:
    status: LearningReviewStatus
    paired_trials: int = 0
    retained_goal_successes: int = 0
    cheap_goal_successes: int = 0
    retained_work_units: int = 0
    cheap_work_units: int = 0
    transfer_contexts: int = 0
    science_qualified: bool = False
    habit_grants: int = 0
    learning_updates: int = 0
    action_authority: bool = False
    reason: str = ""


def _training(
    owner: PersistentCognition,
    labels: tuple[ExternalGoalLabel, ...],
    admission: ExternalTrialAdmission,
) -> tuple[set[str], set[str], set[str]]:
    if not isinstance(labels, tuple) or not 2 <= len(labels) <= _MAX_TRAIN:
        raise MatchedEvidenceRejected("bounded prior training source tuple required")
    originals = {m.memory_id: m for m in owner.memories}
    sessions: set[str] = set()
    training_memory_ids: set[str] = set()
    cues: set[str] = set()
    for label in labels:
        if not isinstance(label, ExternalGoalLabel):
            raise MatchedEvidenceRejected("typed original goal witness pointer required")
        if label.observed_memory_id in training_memory_ids:
            raise MatchedEvidenceRejected("replayed training episode")
        m = originals.get(label.observed_memory_id)
        if m is None:
            raise MatchedEvidenceRejected("prior original L1 Memory missing")
        try:
            v = json.loads(m.content)
            if not isinstance(v, dict) or set(v) != {
                "schema", "session_id", "world_revision", "action_id",
                "binding_id", "action_ref", "source_status", "disposition",
                "reason_code", "evidence_sha256", "cue_tags", "hypothesis",
            } or v["schema"] != "L1_SOURCE_EPISODE_V1" or (
                v["disposition"], v["source_status"], v["reason_code"]
            ) != ("outcome", "executed", "observed_execution"):
                raise MatchedEvidenceRejected("training is not physical observed Action")
            if (
                type(v["world_revision"]) is not int
                or v["world_revision"] < 0
                or not _key(v["session_id"])
                or m.memory_id != (
                    f'l1:{v["session_id"]}:{v["action_id"]}:{v["world_revision"]}'
                )
                or not _sha(v["evidence_sha256"])
                or not isinstance(v["cue_tags"], list)
                or not v["cue_tags"]
                or not all(_key(c) for c in v["cue_tags"])
            ):
                raise MatchedEvidenceRejected("original training lineage mismatch")
        except (ValueError, TypeError, KeyError) as exc:
            raise MatchedEvidenceRejected("malformed original training source") from exc
        if (
            v["evidence_sha256"] not in admission.action_sha256
            or label.goal_source_sha256 not in admission.goal_sha256
        ):
            raise MatchedEvidenceRejected("prior training and goal originals unverified")
        if not label.goal_reached:
            raise MatchedEvidenceRejected("unsuccessful experience is not proven training")
        hint = retrieve_experience(owner, ReuseQuery(
            v["session_id"], v["world_revision"], tuple(v["cue_tags"]),
            frozenset({v["evidence_sha256"]}), max_revision_lag=0,
        ))
        if (
            hint.status is not ReuseStatus.RECALL
            or m.memory_id not in hint.memory_ids
        ):
            raise MatchedEvidenceRejected("L1 original training Memory not source-admitted")
        if v["session_id"] in sessions:
            raise MatchedEvidenceRejected("training sessions not independent")
        sessions.add(v["session_id"])
        training_memory_ids.add(label.observed_memory_id)
        cues.add("/".join(v["cue_tags"]))
    return sessions, training_memory_ids, cues


def review_matched_transfer(
    owner: PersistentCognition,
    *,
    training: tuple[ExternalGoalLabel, ...],
    trials: tuple[ProspectiveTrial, ...],
    admission: ExternalTrialAdmission,
    preregistered_plan_sha256: str,
    min_independent_pairs: int = 2,
) -> MatchedReview:
    """Review paired evidence only; never conclude Memory causation or science GO.

    Same-source SHA and predeclared plan identifiers are contracts, not proof
    of randomization, independent physical readback or identical actual World.
    """
    if not isinstance(owner, PersistentCognition):
        raise MatchedEvidenceRejected("existing Memory owner required")
    if not isinstance(admission, ExternalTrialAdmission):
        raise MatchedEvidenceRejected("external receipts required")
    if not _sha(preregistered_plan_sha256):
        raise MatchedEvidenceRejected("predeclared original plan digest required")
    if type(min_independent_pairs) is not int or not 2 <= min_independent_pairs <= 16:
        raise MatchedEvidenceRejected("bounded pair requirement")
    if not isinstance(trials, tuple) or len(trials) > 2 * _MAX_PAIRS:
        raise MatchedEvidenceRejected("bounded typed paired trials required")
    if not trials:
        return MatchedReview(
            LearningReviewStatus.NO_MATCHED_HOLDOUT,
            reason="S9_two_actions_same_session_not_a_matched_cheap_control",
        )
    if not training:
        return MatchedReview(LearningReviewStatus.NO_GOAL_SOURCE,
                             reason="no_independent_training_goal")
    training_sessions, training_ids, train_cues = _training(owner, training, admission)
    if preregistered_plan_sha256 not in admission.plan_sha256:
        return MatchedReview(LearningReviewStatus.UNVERIFIED,
                             reason="preregistered_source_plan_not_admitted")
    seen_sessions = set(training_sessions)
    pairs: dict[str, dict[TrialArm, ProspectiveTrial]] = {}
    seen_originals: set[str] = set()
    for trial in trials:
        if not isinstance(trial, ProspectiveTrial):
            raise MatchedEvidenceRejected("typed original trial required")
        if trial.session_id in seen_sessions:
            raise MatchedEvidenceRejected("training/holdout or pair session replay")
        seen_sessions.add(trial.session_id)
        if trial.plan_sha256 != preregistered_plan_sha256:
            return MatchedReview(LearningReviewStatus.NON_MATCHED,
                                 reason="trial_not_in_predeclared_experiment")
        arm_records = pairs.setdefault(trial.pair_id, {})
        if trial.arm in arm_records:
            raise MatchedEvidenceRejected("duplicate treatment or cheap arm")
        if not all((
            trial.action_sha256 in admission.action_sha256,
            trial.goal_sha256 in admission.goal_sha256,
            trial.decision_sha256 in admission.decision_sha256,
            trial.cost_sha256 in admission.cost_sha256,
        )):
            return MatchedReview(LearningReviewStatus.UNVERIFIED,
                                 reason="original_action_goal_decision_cost_missing")
        for evidence in (
            trial.action_sha256, trial.goal_sha256,
            trial.decision_sha256, trial.cost_sha256,
        ):
            if evidence in seen_originals:
                raise MatchedEvidenceRejected("replayed source original across trials")
            seen_originals.add(evidence)
        if trial.arm is TrialArm.RETAINED and trial.memory_id not in training_ids:
            raise MatchedEvidenceRejected("retained evidence not from independent training")
        arm_records[trial.arm] = trial
    if len(pairs) < min_independent_pairs:
        return MatchedReview(LearningReviewStatus.NO_TRANSFER,
                             reason="not_enough_independent_paired_holdout")
    retained_wins = cheap_wins = retained_work = cheap_work = 0
    observed_cues: set[str] = set()
    source_head: str | None = None
    for pair in pairs.values():
        if set(pair) != {TrialArm.RETAINED, TrialArm.CHEAP}:
            return MatchedReview(LearningReviewStatus.NO_MATCHED_HOLDOUT,
                                 reason="no_both_arms_for_same_pair")
        active, cheap = pair[TrialArm.RETAINED], pair[TrialArm.CHEAP]
        matched = (
            active.source_head == cheap.source_head
            and active.initial_world_sha256 == cheap.initial_world_sha256
            and active.task_goal_spec_sha256 == cheap.task_goal_spec_sha256
            and active.candidate_set_sha256 == cheap.candidate_set_sha256
            and active.cue_key == cheap.cue_key
        )
        if not matched or (source_head is not None and source_head != active.source_head):
            return MatchedReview(LearningReviewStatus.NON_MATCHED,
                                 reason="different_world_task_candidates_or_source")
        source_head = active.source_head
        retained_wins += int(active.goal_reached)
        cheap_wins += int(cheap.goal_reached)
        retained_work += active.measured_work_units
        cheap_work += cheap.measured_work_units
        if active.cue_key not in train_cues:
            observed_cues.add(active.cue_key)
    if not observed_cues:
        return MatchedReview(LearningReviewStatus.NO_TRANSFER,
                             reason="no_heldout_cue_outside_training")
    if retained_wins == cheap_wins and retained_work == cheap_work:
        status = LearningReviewStatus.CHEAP_NULL_EQUAL
    elif (
        retained_wins >= cheap_wins and retained_work <= cheap_work
    ):
        status = LearningReviewStatus.REVIEW_LIFT_ONLY
    elif cheap_wins >= retained_wins and cheap_work <= retained_work:
        status = LearningReviewStatus.CHEAP_DOMINATES
    else:
        # A goal improvement at higher unpriced resource cost is NOT cheap
        # dominance or measured net benefit. V owns utility calibration.
        status = LearningReviewStatus.TRADEOFF_UNRESOLVED
    return MatchedReview(
        status, len(pairs), retained_wins, cheap_wins,
        retained_work, cheap_work, len(observed_cues),
        reason="all_outcomes_external_review_only_no_causal_or_science_admission",
    )
