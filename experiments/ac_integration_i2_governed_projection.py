"""I2 offline: S17/S10 exact governed scalar -> S11 ephemeral cue projection.

Reuses *actual* existing owners. A projection is NOT an authorized retained
S11 acquisition, L2 activation, an Action, or real native World attestation.
Strong source-matched cheap scalar threshold remains a sufficient Grand Null.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.ac_integration_i1_owner_seam import read_i1_owner_seam
from relay_self.action import ActionState
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.epoch_continuation import read_retained_preference
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningProposalStatus,
)
from relay_self.provenance import Provenance

MANIFEST = Path(__file__).with_name("ac_integration_i2_manifest.json")
FROZEN_DIGEST = "735e6713f905844d5bedfed514605002624779b935a289982fc3344620293d96"
EXPECTED_ACTION = "action-move-backward-1"
REPERTOIRE_ID = "i2-ephemeral-not-a-production-owner"


class I2Rejected(ValueError):
    """No source-qualified proposal or unauthorized promotion allowed."""


@dataclass(frozen=True, slots=True)
class ProjectionGrant:
    grant_id: str
    target_id: str
    feedback_id: str
    source_evidence_id: str
    source_session: str
    from_revision: int
    to_revision: int
    granted: bool
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class I2Result:
    source_evidence_id: str
    s17_feedback_id: str
    s10_old_revision: int
    s10_new_revision: int
    s10_old_value: int
    s10_new_value: int
    s11_old_candidate: str
    s11_new_candidate: str
    s24_reference: str
    cheap_retention_threshold: str
    no_feedback_candidate: str
    always_move_away: str
    changed_by_retention: bool
    new_matches_s24: bool
    cheap_matches_s11: bool
    repertoire_production_committed: bool = False
    action_authorized: bool = False
    new_action_issued: bool = False
    l2_actually_run: bool = False
    physical_source_attested: bool = False
    production_go: bool = False


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    ret = {}
    for k, v in pairs:
        if k in ret:
            raise I2Rejected("duplicate manifest key")
        ret[k] = v
    return ret


def verify_frozen_manifest() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"), object_pairs_hook=_unique)
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != FROZEN_DIGEST:
        raise I2Rejected("prospectively frozen I2 manifest changed")


def cheap_choice(value: int, band: str) -> str:
    if type(value) is not int or not 0 <= value <= 10:
        raise I2Rejected("retained risk scalar invalid")
    if band not in ("near", "far"):
        raise I2Rejected("no source-qualified clearance band")
    wait = (2 if band == "near" else 1) * value
    if wait == 7:
        raise I2Rejected("fixed comparator ties; no invented preference")
    return "WAIT" if wait < 7 else "MOVE_AWAY"


def _project(owner, grant: ProjectionGrant) -> HabitRepertoire:
    """Test-only immutable projection, never an S11 retained owner update."""
    rules = tuple(
        HabitRule(
            habit_id=f"i2-rule:{band}:rev{owner.revision}",
            cue_requirements=(CueFeature("clearance_band", band),),
            candidate_ref=cheap_choice(owner.value, band),
            priority=1,
            provenance=grant.provenance,
        )
        for band in ("near", "far")
    )
    return HabitRepertoire(
        repertoire_id=REPERTOIRE_ID,
        revision=owner.revision,
        rules=rules,
        provenance=grant.provenance,
    )


def evaluate_i2(
    i1_inputs: dict[str, Any],
    owner_commit: LearningCommitResult,
    supplied_commit: LearningCommitResult,
    feedback: LearningFeedbackInterpretation,
    grant: ProjectionGrant | None,
    *,
    consumed_grants: frozenset[str] = frozenset(),
) -> I2Result:
    """Compare a source-grounded next S11 projection to a matched cheap null.

    Caller supplies the exact S10 owner commit and a test-only grant. This
    does not authenticate either caller or physical Mineflayer process.
    """
    if not isinstance(i1_inputs, dict):
        raise I2Rejected("I1 source/owner inputs required")
    if (
        not isinstance(owner_commit, LearningCommitResult)
        or supplied_commit is not owner_commit
    ):
        raise I2Rejected("S10 commit is not exact current caller owner")
    if not isinstance(feedback, LearningFeedbackInterpretation):
        raise I2Rejected("S17 typed feedback required")
    if not isinstance(grant, ProjectionGrant) or grant.granted is not True:
        raise I2Rejected("separate test-only projection grant required")
    if not isinstance(consumed_grants, frozenset) or any(
        type(x) is not str for x in consumed_grants
    ):
        raise I2Rejected("explicit caller replay-set must be typed")
    if grant.grant_id in consumed_grants:
        raise I2Rejected("caller reports replayed scoped projection grant")
    if (
        type(grant.grant_id) is not str
        or not grant.grant_id
        or not isinstance(grant.provenance, Provenance)
    ):
        raise I2Rejected("grant identity/provenance absent")

    before = owner_commit.previous_state
    after = owner_commit.new_state
    rec = owner_commit.record
    observation = i1_inputs.get("owner_receipt")
    supervisor = i1_inputs.get("supervisor")
    try:
        action1 = supervisor.get(EXPECTED_ACTION)
    except (AttributeError, ValueError) as exc:
        raise I2Rejected("first Action missing from current S18–S29 owner") from exc
    if (
        not action1.is_current_snapshot
        or action1.state is not ActionState.OUTCOME
        or feedback.status is not LearningFeedbackInterpretationStatus.PRODUCED
        or feedback.feedback is None
        or feedback.feedback.direction is not FeedbackDirection.INCREASE
        or feedback.action_id != action1.action_id
        or feedback.skill_execution_id != action1.skill_execution_id
        or feedback.intent_id != action1.intent_id
        or feedback.world_provenance != action1.events[-1].provenance
        or feedback.outcome_ref != feedback.feedback.consequence_ref
        or rec.feedback_id != feedback.feedback.feedback_id
        or rec.feedback_provenance != feedback.feedback.provenance
        or rec.authority_id != "s18-learning-authority"
        or rec.status is not LearningProposalStatus.UPDATED
        or rec.target_id != "risk_weight"
        or rec.rule_id != "bounded-risk-step"
        or rec.rule_version != 1
        or rec.previous_revision != 0
        or rec.committed_revision != 1
        or rec.previous_value != 3
        or rec.resulting_value != 4
        or before.target_id != "risk_weight"
        or before.value != 3
        or before.revision != 0
        or after.value != 4
        or after.revision != 1
        or after.last_update is not rec
        or owner_commit.proposal.feedback is not feedback.feedback
        or i1_inputs.get("current_retained") is not after
        or i1_inputs.get("supplied_retained") is not after
    ):
        raise I2Rejected("S17/S10 actual Action-feedback-commit lineage unqualified")
    if not hasattr(observation, "source_receipt"):
        raise I2Rejected("S29 correlation source missing")
    source = observation.source_receipt
    obs = source.source
    evidence = source.evidence
    if (
        type(grant.source_evidence_id) is not str
        or grant.source_evidence_id != evidence.evidence_id
        or grant.source_session != obs.session_id
        or grant.feedback_id != rec.feedback_id
        or grant.target_id != after.target_id
        or type(grant.from_revision) is not int
        or type(grant.to_revision) is not int
        or grant.from_revision != before.revision
        or grant.to_revision != after.revision
        or observation.request_id != "s29-probe:one.1"
    ):
        raise I2Rejected("grant does not bind exact S17/S29/caller-epoch source")

    # S19 still authoritatively gates retained snapshot reads.
    read_retained_preference(
        after, i1_inputs["supplied_retained"],
        required_target_id="risk_weight", expected_revision=1,
        provenance=grant.provenance,
    )
    cm = evidence.threat_clearance_cm
    if cm not in (20, 180):
        raise I2Rejected("outside prospectively frozen World distances")
    band = "near" if cm <= 100 else "far"
    old_repertoire = _project(before, grant)
    new_repertoire = _project(after, grant)
    cue = HabitCue(
        cue_id=f"i2-s29-{observation.request_id}",
        features=(CueFeature("clearance_band", band),),
        provenance=obs.provenance,
    )
    old_selection = select_habit(old_repertoire, cue)
    new_selection = select_habit(new_repertoire, cue)
    if (
        old_selection.status is not HabitSelectionStatus.SELECTED
        or new_selection.status is not HabitSelectionStatus.SELECTED
    ):
        raise I2Rejected("actual S11 selection was ambiguous")
    # I1 is the already-qualified A/B/C read-only seam. Its source controls
    # and S24 typed independent cognition remain unchanged.
    existing = read_i1_owner_seam(**{**i1_inputs, "repertoire": new_repertoire})
    old = old_selection.selected_candidate_ref
    new = new_selection.selected_candidate_ref
    if (
        existing.habit_candidate != new
        or existing.source_session != obs.session_id
        or existing.evidence_id != evidence.evidence_id
        or existing.retained_revision != after.revision
        or existing.reference_candidate != cheap_choice(after.value, band)
    ):
        raise I2Rejected("S29/S24/I1 independent source reference mismatch")
    assert old is not None and new is not None
    return I2Result(
        source_evidence_id=evidence.evidence_id,
        s17_feedback_id=rec.feedback_id,
        s10_old_revision=before.revision,
        s10_new_revision=after.revision,
        s10_old_value=before.value,
        s10_new_value=after.value,
        s11_old_candidate=old,
        s11_new_candidate=new,
        s24_reference=existing.reference_candidate,
        cheap_retention_threshold=cheap_choice(after.value, band),
        no_feedback_candidate=cheap_choice(before.value, band),
        always_move_away="MOVE_AWAY",
        changed_by_retention=old != new,
        new_matches_s24=new == existing.reference_candidate,
        cheap_matches_s11=new == cheap_choice(after.value, band),
    )
