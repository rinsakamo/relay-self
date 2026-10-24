"""DEV-only distinction: developer-specified habits vs synthetic proposal examples.

No L2 execution, S17/S10 retained learning, L0 installation, or Action issuer.
The original HabitRule and select_habit are reused without new runtime owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from experiments.zombie_melee_perception_dev import (
    L0ContactStatus,
    L1MotionStatus,
    ZombieMeleeCueReview,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.provenance import Provenance


class PatternLineageRejected(ValueError):
    """Reject mixed origins, identity confusion and unfounded learning claims."""


class PatternOrigin(str, Enum):
    DEVELOPER_SCAFFOLD = "DEVELOPER_SCAFFOLD"
    SYNTHETIC_PROPOSAL_EXAMPLE = "SYNTHETIC_PROPOSAL_EXAMPLE"


class PatternLane(str, Enum):
    L0 = "L0"
    L1 = "L1"


_EXPECTED_TRIGGER = {
    PatternLane.L0: L0ContactStatus.POSSIBLE_CONTACT.value,
    PatternLane.L1: L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC.value,
}
_FEATURE = {PatternLane.L0: "zombie_l0_cue", PatternLane.L1: "zombie_l1_cue"}
_PROVENANCE = {
    PatternOrigin.DEVELOPER_SCAFFOLD: "developer_scaffold_dev",
    PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE: "synthetic_proposal_dev",
}


def _token(name: str, value: object) -> None:
    if (
        type(value) is not str or not value
        or value != value.strip() or any(x.isspace() for x in value)
    ):
        raise PatternLineageRejected(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class PatternLineage:
    """Metadata for *one* bounded original HabitRule, never a learned grant."""

    self_id: str
    origin: PatternOrigin
    lane: PatternLane
    rule: HabitRule
    supporting_source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _token("self_id", self.self_id)
        if not isinstance(self.origin, PatternOrigin):
            raise PatternLineageRejected("unsupported pattern origin")
        if not isinstance(self.lane, PatternLane):
            raise PatternLineageRejected("unsupported cognitive lane")
        if not isinstance(self.rule, HabitRule):
            raise PatternLineageRejected("existing HabitRule required")
        if self.rule.provenance.source != _PROVENANCE[self.origin]:
            raise PatternLineageRejected("forged origin provenance")
        if self.rule.cue_requirements != (
            CueFeature(_FEATURE[self.lane], _EXPECTED_TRIGGER[self.lane]),
        ):
            raise PatternLineageRejected("unexpected cue or lane")
        refs = self.supporting_source_refs
        if type(refs) is not tuple or any(type(x) is not str for x in refs):
            raise PatternLineageRejected("typed supporting refs required")
        if self.origin is PatternOrigin.DEVELOPER_SCAFFOLD:
            if refs:
                raise PatternLineageRejected("scaffold cannot claim learning")
        elif (
            len(refs) < 2 or len(set(refs)) != len(refs)
            or any(not x.startswith("synthetic-dev:") for x in refs)
        ):
            raise PatternLineageRejected(
                "synthetic example requires distinct synthetic-only refs"
            )

    @property
    def verified_self_learned(self) -> bool:
        """Neither a manual baseline nor a mock L2 proposal is learned."""
        return False


@dataclass(frozen=True, slots=True)
class PatternSelectionReview:
    """A side-by-side read-only habit match, not a motor or learning grant."""

    self_id: str
    cue_source_ref: str
    origin: PatternOrigin
    lane: PatternLane
    selected_candidate_ref: str | None
    status: HabitSelectionStatus
    learned_from_world: bool = False
    authorized_for_action: bool = False
    admitted_to_l0: bool = False


def _make_rule(
    *, pattern_id: str, lane: PatternLane,
    origin: PatternOrigin, candidate_ref: str,
) -> HabitRule:
    _token("pattern_id", pattern_id)
    _token("candidate_ref", candidate_ref)
    return HabitRule(
        habit_id=pattern_id,
        cue_requirements=(
            CueFeature(_FEATURE[lane], _EXPECTED_TRIGGER[lane]),
        ),
        candidate_ref=candidate_ref,
        priority=0,
        provenance=Provenance(
            _PROVENANCE[origin], f"{origin.value}:{pattern_id}"
        ),
    )


def manual_zombie_pattern(*, self_id: str, lane: PatternLane) -> PatternLineage:
    """Hand-authored target behavior, NOT a Self experience or learned rule."""
    _token("self_id", self_id)
    if not isinstance(lane, PatternLane):
        raise PatternLineageRejected("unsupported cognitive lane")
    return PatternLineage(
        self_id=self_id,
        lane=lane,
        origin=PatternOrigin.DEVELOPER_SCAFFOLD,
        rule=_make_rule(
            pattern_id=f"manual_zombie_{lane.value.lower()}",
            lane=lane, origin=PatternOrigin.DEVELOPER_SCAFFOLD,
            candidate_ref=f"dev_only_dodge_{lane.value.lower()}",
        ),
    )


def synthetic_proposal_example(
    *, self_id: str, lane: PatternLane, supporting_source_refs: tuple[str, ...],
) -> PatternLineage:
    """Fixture for an eventual L2 proposal, not a claim L2 actually ran."""
    _token("self_id", self_id)
    if not isinstance(lane, PatternLane):
        raise PatternLineageRejected("unsupported cognitive lane")
    return PatternLineage(
        self_id=self_id,
        lane=lane,
        origin=PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE,
        rule=_make_rule(
            pattern_id=f"synthetic_zombie_{lane.value.lower()}",
            lane=lane, origin=PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE,
            candidate_ref=f"dev_only_dodge_{lane.value.lower()}",
        ),
        supporting_source_refs=supporting_source_refs,
    )


def select_zombie_pattern(
    *, review: ZombieMeleeCueReview, pattern: PatternLineage,
) -> PatternSelectionReview:
    """Pass existing cue to existing Habit selector; never grant an Action."""
    if not isinstance(review, ZombieMeleeCueReview):
        raise PatternLineageRejected("typed zombie perception review required")
    if not isinstance(pattern, PatternLineage):
        raise PatternLineageRejected("typed pattern provenance required")
    if review.self_id != pattern.self_id:
        raise PatternLineageRejected("foreign Self pattern")
    if not review.current_source_ref.startswith(
        f"present:{review.session_id}:"
    ):
        raise PatternLineageRejected("invalid current cue source")
    if pattern.lane is PatternLane.L0:
        value = review.l0_contact
        if not isinstance(value, L0ContactStatus):
            raise PatternLineageRejected("typed L0 cue required")
    else:
        value = review.l1_motion
        if not isinstance(value, L1MotionStatus):
            raise PatternLineageRejected("typed L1 cue required")
    # A source-aware read-only Habit is not a retained learning commit.
    repertoire = HabitRepertoire(
        repertoire_id=f"dev_{pattern.rule.habit_id}",
        revision=0,
        rules=(pattern.rule,),
        provenance=pattern.rule.provenance,
    )
    cue = HabitCue(
        cue_id=f"dev_{pattern.rule.habit_id}_cue",
        features=(CueFeature(_FEATURE[pattern.lane], value.value),),
        provenance=Provenance("dev_read_only_melee", review.current_source_ref),
    )
    selection = select_habit(repertoire, cue)
    return PatternSelectionReview(
        self_id=pattern.self_id,
        cue_source_ref=review.current_source_ref,
        origin=pattern.origin,
        lane=pattern.lane,
        selected_candidate_ref=selection.selected_candidate_ref,
        status=selection.status,
    )


def compare_manual_and_synthetic(
    *, review: ZombieMeleeCueReview,
    manual: PatternLineage, proposal: PatternLineage,
) -> tuple[PatternSelectionReview, PatternSelectionReview]:
    """Offline comparison of choice only, not independent World outcomes."""
    if (
        manual.origin is not PatternOrigin.DEVELOPER_SCAFFOLD
        or proposal.origin is not PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE
        or manual.lane is not proposal.lane
    ):
        raise PatternLineageRejected("independent manual/proposal arms required")
    return (
        select_zombie_pattern(review=review, pattern=manual),
        select_zombie_pattern(review=review, pattern=proposal),
    )
