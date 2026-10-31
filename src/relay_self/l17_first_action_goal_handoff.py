"""L17: L16 original prefix -> independent L14/L13 Goal handoff, read-only.

Nothing in this module mints an independent Goal owner, S16 receipt, grant,
training pair or physical authorization. An operator-only L16 result does not
become an external per-Action reward, even when it says NOT_REACHED.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.l16_first_action_goal_originals import (
    L16FirstActionWindow,
    L16GoalPlan,
    inspect_l16_first_action_prefix,
)
from relay_self.l10_world_body_cue_learning import WorldBodyCueWitness
from relay_self.l13_independent_goal_receipt import (
    L13IndependentSourceAdmission,
    L13ReceiptStatus,
    L13ReceiptTriplet,
)
from relay_self.l14_original_bridge_goal_window import (
    CRITERION_KEYS,
    CRITERION_SCHEMA,
    L14GoalWindow,
    L14SourceRejected,
    _json,
    audit_l14_native_goal_window,
)

SCHEMA = "L17_S49_INDEPENDENT_GOAL_READONLY_HANDOFF_V1"


class L17HandoffRejected(ValueError):
    """The previous original or independent reviewer source does not agree."""


class L17HandoffStatus(str, Enum):
    WAITING_FOR_EXTERNAL_ORIGINALS = "waiting_for_independent_s16_goal_originals"
    SOURCE_SHAPED_L10_CANDIDATE = "source_shaped_l10_candidate_not_qualified"
    UNDETERMINED_NO_GOAL_LABEL = "undetermined_no_goal_label"


@dataclass(frozen=True, slots=True)
class L17IndependentInputs:
    """Externally supplied originals, NEVER generated from L16's outcome.

    L13 typed objects carry preexisting owner-controlled S16 terminal and
    later-epoch SelfWorld/SelfBody. Their source/authenticity cannot be
    authenticated by L17 or a SHA claim.
    """

    criterion_original: bytes
    admitted_criterion_sha256: frozenset[str]
    receipt_triplet: L13ReceiptTriplet
    admission: L13IndependentSourceAdmission
    current: WorldBodyCueWitness


@dataclass(frozen=True, slots=True)
class L17ReadOnlyHandoff:
    schema: str
    status: L17HandoffStatus
    l16_first_action: L16FirstActionWindow
    l14_independent_goal: L14GoalWindow | None
    l10_previous_epoch_candidate_available: bool
    pending_external_s16_original: bool
    pending_independent_goal_original: bool
    pending_independent_original_authentication: bool = True
    pending_physical_nonintervention_review: bool = True
    qualified_real_training_pairs: int = 0
    real_l10_adoptions: int = 0
    s10_updates: int = 0
    s11_habit_grants: int = 0
    new_actions: int = 0
    new_worlds: int = 0


def review_l17_first_action_goal(
    *,
    received_original: bytes,
    sent_original: bytes,
    s7_receipt: dict,
    plan: L16GoalPlan,
    plan_original: bytes,
    action_id: str,
    session_id: str,
    before_seq: int,
    dispatch_seq: int,
    cleanup_seq: int,
    after_seq: int,
    first_probe_seq: int,
    second_probe_seq: int,
    first_probe_request_id: str,
    second_probe_request_id: str,
    external: L17IndependentInputs | None = None,
) -> L17ReadOnlyHandoff:
    """Replay the one captured S49 prefix; never backfill a physical reward.

    Without independent originals: retain only the bounded L16 DEV geometry.
    With independent originals: verify L14's exact same source and Goal
    criterion, then return only the *source-shaped* L10 previous-epoch
    candidate. An independent V/R original readback is still required.
    """
    l16 = inspect_l16_first_action_prefix(
        received_original=received_original, sent_original=sent_original,
        s7_receipt=s7_receipt, plan=plan, plan_original=plan_original,
        action_id=action_id, session_id=session_id, before_seq=before_seq,
        dispatch_seq=dispatch_seq, cleanup_seq=cleanup_seq,
        after_seq=after_seq, first_probe_seq=first_probe_seq,
        second_probe_seq=second_probe_seq,
        first_probe_request_id=first_probe_request_id,
        second_probe_request_id=second_probe_request_id,
    )
    if external is None:
        return L17ReadOnlyHandoff(
            schema=SCHEMA,
            status=L17HandoffStatus.WAITING_FOR_EXTERNAL_ORIGINALS,
            l16_first_action=l16, l14_independent_goal=None,
            l10_previous_epoch_candidate_available=False,
            pending_external_s16_original=True,
            pending_independent_goal_original=True,
        )
    if not isinstance(external, L17IndependentInputs):
        raise L17HandoffRejected("external originals must use typed independent inputs")
    raw = external.criterion_original
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise L17HandoffRejected("one exact external criterion original required")
    try:
        criterion = _json(raw)
    except L14SourceRejected as exc:
        raise L17HandoffRejected("external criterion original is invalid") from exc
    if (set(criterion) != CRITERION_KEYS
            or criterion.get("schema") != CRITERION_SCHEMA
            or criterion.get("session_id") != session_id
            or criterion.get("action_id") != action_id
            or external.receipt_triplet.raw_native_probe
            != received_original.splitlines(keepends=True)[before_seq]
            or hashlib.sha256(raw).hexdigest()
            not in external.admitted_criterion_sha256):
        raise L17HandoffRejected("foreign/pre-Action criterion/Present originals")
    # An operator target is not itself an external Goal source. Compare both
    # *original* criteria before asking L14 to join distinct S/R/V sources.
    for key, expected in (
        ("target_x", plan.target_x),
        ("target_z", plan.target_z),
        ("tolerance_m", plan.tolerance_m),
        ("stable_probe_delta_max_m", plan.stable_probe_delta_max_m),
    ):
        value = criterion.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value != expected:
            raise L17HandoffRejected("independent Goal criterion differs from pre-World plan")
    l14 = audit_l14_native_goal_window(
        received_original=received_original,
        sent_original=sent_original, s7_source_receipt=s7_receipt,
        external_criterion_original=raw,
        independently_admitted_criterion_sha256=external.admitted_criterion_sha256,
        item=external.receipt_triplet,
        admission=external.admission,
        current=external.current,
    )
    if (
        l14.source_session_id != l16.session_id
        or l14.action_id != l16.action_id
        or l14.before_native_seq != l16.before_seq
        or l14.action_end_native_seq != l16.after_seq
        or l14.goal_probe_seq != l16.goal_probe_seq
        or l14.second_stable_probe_seq != l16.second_goal_probe_seq
        or l14.original_received_sha256 != l16.received_sha256
        or l14.original_sent_sha256 != l16.sent_sha256
        or l14.observed_goal_status != l16.observed_goal_status
        or not math.isclose(
            l14.goal_error_probe_1_m, l16.distance_first_m,
            abs_tol=1e-10,
        )
        or not math.isclose(
            l14.goal_error_probe_2_m, l16.distance_second_m,
            abs_tol=1e-10,
        )
    ):
        raise L17HandoffRejected("L14 independent audit disagrees with L16 source window")
    has_candidate = (
        l14.l13_source_shaped_candidate.status
        is L13ReceiptStatus.SOURCE_SHAPED_GOAL_CANDIDATE
        and l14.l13_source_shaped_candidate.prior_l10 is not None
    )
    if has_candidate != (l16.observed_goal_status in ("REACHED", "NOT_REACHED")):
        raise L17HandoffRejected("ambiguous source promoted or clear source lost label")
    return L17ReadOnlyHandoff(
        schema=SCHEMA,
        status=(
            L17HandoffStatus.SOURCE_SHAPED_L10_CANDIDATE if has_candidate
            else L17HandoffStatus.UNDETERMINED_NO_GOAL_LABEL
        ),
        l16_first_action=l16, l14_independent_goal=l14,
        l10_previous_epoch_candidate_available=has_candidate,
        pending_external_s16_original=False,
        pending_independent_goal_original=False,
    )
