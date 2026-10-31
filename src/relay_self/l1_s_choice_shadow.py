"""L7 read-only comparison: S42/S49 World choice vs L6 L1 experience.

The S owner supplies the native threat, current retained S10 state and its
own World choice. This module only rechecks the existing pure S42 function and
records a contrast. It has no Action issuer, preference commit or Habit grant.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat
from relay_self.contextual_shadow import ContextualStatus
from relay_self.learning import LearningPreferenceState
from relay_self.learning_epoch import LearningEpochResult
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldConditionedChoice,
    select_world_conditioned_choice,
)


class SChoiceShadowRejected(ValueError):
    """A source or decision pointer cannot be linked to the same S epoch."""


class SChoiceContrastStatus(str, Enum):
    WITHHELD = "retention_off"
    INSUFFICIENT = "no_admissible_l1_proposal"
    AGREES = "l1_agrees_with_s"
    L1_DIFFERS = "l1_shadow_differs_from_s"
    CHEAP_DIFFERS = "cheap_memory_rule_differs_from_s"


@dataclass(frozen=True, slots=True)
class SChoiceContrast:
    status: SChoiceContrastStatus
    s_choice: WorldChoiceKind
    l1_shadow_ref: str | None
    s_session_id: str
    probe_seq: int
    source_revision: int
    original_probe_sha256: str
    candidate_differs: bool
    s_choice_kept: bool = True
    action_authority: bool = False
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


def compare_s_choice_with_l1(
    *,
    native: NativeThreat,
    retained: LearningPreferenceState,
    s_choice: WorldConditionedChoice,
    learning: LearningEpochResult,
    retention_enabled: bool,
) -> SChoiceContrast:
    """Compare one exact S-owned World choice to the L1 shadow for that probe.

    The caller must independently authenticate original native and goal bytes.
    Digest membership here checks only the already supplied S source claims.
    The original S choice is always kept; no L1 output can override L0.
    """
    if (
        not isinstance(native, NativeThreat)
        or not isinstance(retained, LearningPreferenceState)
        or not isinstance(s_choice, WorldConditionedChoice)
        or not isinstance(learning, LearningEpochResult)
        or type(retention_enabled) is not bool
    ):
        raise SChoiceShadowRejected("typed S native/retained/choice and L snapshot required")
    current = learning.current
    if (
        current.session_id != s_choice.session_id
        or current.source_provenance != s_choice.provenance
        or native.observation.session_id != current.session_id
        or native.observation.provenance != current.source_provenance
        or native.observation.seq != s_choice.probe_seq
        or native.observation.request_id != s_choice.request_id
        or native.entity_id != s_choice.entity_id
        or current.original_probe_sha256 not in learning.admitted_current_probe_sha256
        or learning.no_memory_action_ref != s_choice.selection.value
        or learning.advice.original_no_memory_ref not in (
            None, s_choice.selection.value
        )
        or not (
            learning.learning_updates == learning.habit_grants == 0
            and not learning.action_authority
            and not learning.physical_goal_improvement_attested
            and not learning.advice.action_authority
        )
    ):
        raise SChoiceShadowRejected("foreign, stale, unadmitted or mismatched S/L choice")
    # Reuse S's original source validation and fixed World decision, not a
    # second decision heuristic or trust in the dataclass label.
    try:
        recomputed = select_world_conditioned_choice(
            native, retained,
            expected_session_id=s_choice.session_id,
            expected_entity_id=s_choice.entity_id,
        )
    except ValueError as exc:
        raise SChoiceShadowRejected("S native decision cannot be reproduced") from exc
    if s_choice != recomputed or s_choice.action_authorized:
        raise SChoiceShadowRejected("S original decision differs from source replay")
    if retention_enabled and learning.advice.status in (
        ContextualStatus.SHADOW_DIFFERENCE,
        ContextualStatus.CHEAP_EQUIVALENT,
        ContextualStatus.NO_MEMORY_EQUAL,
    ):
        proposal = learning.advice.proposed_action_ref
        if (
            proposal not in (WorldChoiceKind.WAIT.value, WorldChoiceKind.MOVE_AWAY.value)
            or proposal != learning.candidate_action_ref
        ):
            raise SChoiceShadowRejected("L1 candidate differs from existing evidence review")
    else:
        proposal = None
        if learning.candidate_action_ref != s_choice.selection.value:
            raise SChoiceShadowRejected("non-admitted L1 cannot displace S baseline")

    if not retention_enabled:
        status = SChoiceContrastStatus.WITHHELD
    elif proposal is None:
        status = SChoiceContrastStatus.INSUFFICIENT
    elif proposal == s_choice.selection.value:
        status = SChoiceContrastStatus.AGREES
    elif learning.advice.status is ContextualStatus.CHEAP_EQUIVALENT:
        status = SChoiceContrastStatus.CHEAP_DIFFERS
    else:
        status = SChoiceContrastStatus.L1_DIFFERS

    return SChoiceContrast(
        status=status,
        s_choice=s_choice.selection,
        l1_shadow_ref=proposal,
        s_session_id=s_choice.session_id,
        probe_seq=s_choice.probe_seq,
        source_revision=current.source_revision,
        original_probe_sha256=current.original_probe_sha256,
        candidate_differs=proposal is not None and proposal != s_choice.selection.value,
    )
