"""S Lane S2: source-bound read-only L1 candidate from existing S11 selector.

L1 never returns an Action grant, a learned Habit, or an instruction to override
S49 L0. The optional L2 observer is separately owned by existing S60-A/B1.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import WorldChoiceKind, WorldConditionedChoice


class S2CandidateRejected(ValueError):
    """A source-unbound or authority-bearing candidate is not admissible."""


@dataclass(frozen=True, slots=True)
class S2CandidateReview:
    session_id: str
    event_seq: int
    probe_seq: int
    l0_selection: str
    l1_status: str
    l1_candidate: str | None
    l1_repertoire_revision: int
    l1_source: str
    effective_selection: str
    action_authorized_by_l1: bool = False
    learned_habit_claimed: bool = False
    l2_used_for_action: bool = False


def preconfigured_wait_repertoire() -> HabitRepertoire:
    """Original S11 read-only matching over an explicitly NON-learned rule.

    The only possible L1 recommendation is WAIT on a far source observation.
    It cannot create a new MOVE_AWAY issuance, and never implies S11 acquisition.
    """
    p = Provenance("s2-product-preconfigured", "not-learned-far-wait")
    return HabitRepertoire(
        repertoire_id="s2-safe-only-not-learned",
        revision=0,
        rules=(HabitRule(
            habit_id="s2-preconfigured-far-wait",
            cue_requirements=(CueFeature("native_threat_band", "far"),),
            candidate_ref="WAIT", priority=1, provenance=p,
        ),),
        provenance=p,
    )


class S2ReadOnlyCandidates:
    """One strict source cursor. The result is observation-only, not authority."""

    def __init__(self, session_id: str, repertoire: HabitRepertoire) -> None:
        if (
            not isinstance(session_id, str) or not session_id
            or not isinstance(repertoire, HabitRepertoire)
            or repertoire.revision != 0
            or any(rule.candidate_ref != "WAIT" for rule in repertoire.rules)
        ):
            raise S2CandidateRejected(
                "explicit safe-only preconfigured S11 repertoire required"
            )
        self.session_id = session_id
        self.repertoire = repertoire
        self._last_probe_seq = -1

    def review(self, choice: WorldConditionedChoice, event_seq: int) -> S2CandidateReview:
        if (
            not isinstance(choice, WorldConditionedChoice)
            or type(event_seq) is not int or event_seq < 0
            or choice.session_id != self.session_id
            or choice.probe_seq <= event_seq
            or choice.probe_seq <= self._last_probe_seq
            or choice.provenance.source != "mineflayer"
            or choice.action_authorized
            or choice.selection not in (WorldChoiceKind.WAIT, WorldChoiceKind.MOVE_AWAY)
            or ((choice.distance_m < choice.threshold_m)
                != (choice.selection is WorldChoiceKind.MOVE_AWAY))
        ):
            raise S2CandidateRejected("fresh same-session S49 source required")
        self._last_probe_seq = choice.probe_seq
        cue = HabitCue(
            f"s2-native-cue-{self.session_id}-{choice.probe_seq}",
            (CueFeature(
                "native_threat_band",
                "near" if choice.distance_m < choice.threshold_m else "far",
            ),),
            choice.provenance,
        )
        selection = select_habit(self.repertoire, cue)
        candidate = (
            selection.selected_candidate_ref
            if selection.status is HabitSelectionStatus.SELECTED else None
        )
        # The genuine S49 L0 route is immutable here; no S11 rule issues Action.
        return S2CandidateReview(
            session_id=self.session_id,
            event_seq=event_seq, probe_seq=choice.probe_seq,
            l0_selection=choice.selection.value,
            l1_status=selection.status.value,
            l1_candidate=candidate,
            l1_repertoire_revision=self.repertoire.revision,
            l1_source=choice.provenance.reference,
            effective_selection=choice.selection.value,
        )
