"""R2-3c DEV: original Resident Owner freezes a FIRST reJOIN Question L1 request.

The existing original Stage28 CoverageAdoptionTurn and its ADOPT/HOLD/DECLINE
choice *vocabulary* are reused. Stage28's first-login source verifier is NOT
reused. This CPU-only opt-in request is separately typed and cannot be passed
to Stage28's original GPU issuer, adoption or physical paths.

The existing Resident Owner holds its registration weakly. No second owner,
store, GPU ticket, result, memory writer or physical issuer is introduced.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from uuid import uuid4

from relay_self.bd1b_coverage_adoption_turn_dev import CHOICES
from relay_self.provenance import Provenance
from relay_self.r2_3b_original_rejoin_l1_source_compare_dev import (
    R23BOriginalL1SourceComparison,
    r23b_original_rejoin_inquiry_is_live,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    project_identity_context,
)


class R23COriginalRejoinRequestHold(RuntimeError):
    """Original first-reJOIN L1 CPU request is absent, changed or stale."""


def _digest(turn_source: R23BOriginalL1SourceComparison,
            request: BoundedChoiceRequest, cohort_scopes: tuple) -> str:
    """Local mutation detector; SHA-256 is NOT an authenticated source receipt."""
    return hashlib.sha256(repr((
        turn_source.self_id,
        turn_source.current.source_revision_refs,
        turn_source.source_pair_revision,
        turn_source.original_inquiry,
        turn_source.current.schema.revision,
        cohort_scopes,
        request,
    )).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class R23CFrozenOriginalRejoinL1:
    """One registered Original Owner question decision, never GPU admission."""

    self_id: str
    owner: object
    source: R23BOriginalL1SourceComparison
    cohort_owners: tuple[object, object]
    cohort_scopes: tuple[tuple[int, str, int], tuple[int, str, int]]
    cohort_probes: tuple[object, object]
    intent_owner: object
    intent_events: tuple
    retained: object
    continuity_revision: int
    work_ref: str
    request: BoundedChoiceRequest
    request_sha256: str
    model_invoked: bool = False
    question_adopted: bool = False
    intent_committed: bool = False
    memory_written: bool = False
    physical_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.source) is not R23BOriginalL1SourceComparison
            or self.owner is not self.source.original_owner
            or self.source.self_id != self.self_id
            or type(self.cohort_owners) is not tuple
            or len(self.cohort_owners) != 2
            or type(self.cohort_scopes) is not tuple
            or len(self.cohort_scopes) != 2
            or type(self.cohort_probes) is not tuple
            or len(self.cohort_probes) != 2
            or type(self.intent_events) is not tuple
            or type(self.continuity_revision) is not int
            or self.continuity_revision < 0
            or not self.work_ref.startswith("rejoin-coverage-work-")
            or type(self.request) is not BoundedChoiceRequest
            or not self.request.request_id.startswith("rejoin-coverage-request-")
            or self.request.focus != self.source.original_inquiry.question_ref
            or self.request.choices != CHOICES
            or self.request.think_allowed is not False
            or self.request.identity_context is None
            or len(self.request.context) != 1
            or self.request.context[0].key != "current_coverage_inquiry"
            or self.request_sha256 != _digest(
                self.source, self.request, self.cohort_scopes,
            )
            or any((
                self.model_invoked, self.question_adopted,
                self.intent_committed, self.memory_written,
                self.physical_authorized,
            ))
        ):
            raise R23COriginalRejoinRequestHold(
                "only qualified original reJOIN frozen Question request is supported"
            )


@dataclass(frozen=True, slots=True)
class R23COriginalRejoinL1Comparison:
    """Original request and R2-3b Context agree; no inference authority."""

    self_id: str
    request_id: str
    choice_ids: tuple[str, ...]
    question_ref: str
    need_signal_ref: str
    schema_revision: int
    source_revision_refs: tuple[str, str, str]
    request_sha256: str
    original_owner: object
    request_is_registered: bool = True
    model_invoked: bool = False
    l1_input_switched: bool = False
    action_issue_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or self.choice_ids != tuple(choice.choice_id for choice in CHOICES)
            or type(self.source_revision_refs) is not tuple
            or len(self.source_revision_refs) != 3
            or not self.request_id or not self.question_ref
            or not self.need_signal_ref or not self.request_sha256
            or self.request_is_registered is not True
            or self.model_invoked or self.l1_input_switched
            or self.action_issue_authorized
        ):
            raise R23COriginalRejoinRequestHold(
                "registered request comparison is diagnostic, not L1 admission"
            )


def _original_source(*, bridge, self_id: str) -> R23BOriginalL1SourceComparison:
    resident = getattr(bridge, "cognitive_work", None)
    if (
        resident is None
        or getattr(bridge, "inference_lane", None) is not None
        or not isinstance(getattr(bridge, "owners", None), dict)
        or self_id not in ("A", "B")
        or getattr(resident, "owners", {}).get(self_id)
        is not bridge.owners.get(self_id)
    ):
        raise R23COriginalRejoinRequestHold(
            "original disconnected CPU Owner required, no GPU/L1 submission"
        )
    return resident.read_rejoined_l1_source_compatibility_cpu(
        bridge=bridge, self_id=self_id,
    )


def prepare_r23c_original_rejoin_l1_cpu(*, bridge, self_id: str) -> R23CFrozenOriginalRejoinL1:
    """Use existing Original Owner + existing ADOPT/HOLD/DECLINE choice schema.

    The request is CPU-frozen/weakly registered but cannot enter the old
    Stage28 GPU path or write a Question. No new Skill/Target is fabricated.
    """
    resident = getattr(bridge, "cognitive_work", None)
    if resident is None:
        raise R23COriginalRejoinRequestHold("missing original Owner")
    with resident.lock:
        try:
            source = _original_source(bridge=bridge, self_id=self_id)
            owner = resident.owners[self_id]
            owner._eligible()
            if (
                source.original_owner is not owner
                or getattr(resident, "_normal_second_rejoin_cut", None) is not None
            ):
                raise R23COriginalRejoinRequestHold("foreign or second reJOIN")
            retained = owner.retained
            events = owner.intent.events
            intent = owner.intent.current_intent
            continuity = retained.exploration_continuity
            if continuity is not None and continuity.self_id != self_id:
                raise R23COriginalRejoinRequestHold("foreign cognition continuity")
            revision = 0 if continuity is None else continuity.revision
            ids = ("A", "B")
            cohort_owners = tuple(resident.owners[sid] for sid in ids)
            cohort_scopes = tuple(resident.current_scope(sid) for sid in ids)
            cohort_probes = tuple(
                resident.owners[sid].current_worldbody_observation for sid in ids
            )
            inquiry = source.original_inquiry
            context = CognitionDatum.from_value(
                "current_coverage_inquiry",
                {
                    **asdict(inquiry),
                    "meaning": inquiry.meaning,
                    "epistemic_status": inquiry.epistemic_status.value,
                    "source_revision_refs": source.current.source_revision_refs,
                    "source_pair_revision": source.source_pair_revision,
                },
                Provenance("coverage-inquiry", inquiry.question_ref),
            )
            request = BoundedChoiceRequest(
                request_id="rejoin-coverage-request-" + uuid4().hex,
                instruction=(
                    "Choose whether to adopt this current observation coverage "
                    "inquiry as your own OPEN Question."
                ),
                intent_id=None if intent is None else intent.intent_id,
                focus=inquiry.question_ref,
                choices=CHOICES,
                context=(context,),
                identity_context=project_identity_context(retained.identity),
                think_allowed=False,
            )
            turn = R23CFrozenOriginalRejoinL1(
                self_id=self_id, owner=owner, source=source,
                cohort_owners=cohort_owners,
                cohort_scopes=cohort_scopes,
                cohort_probes=cohort_probes,
                intent_owner=owner.intent, intent_events=events,
                retained=retained, continuity_revision=revision,
                work_ref="rejoin-coverage-work-" + uuid4().hex,
                request=request,
                request_sha256=_digest(source, request, cohort_scopes),
            )
            if (
                _original_source(bridge=bridge, self_id=self_id) != source
                or owner.intent.events != events
                or owner.retained is not retained
                or any(
                    resident.owners[sid] is not cohort_owners[i]
                    or resident.current_scope(sid) != cohort_scopes[i]
                    or resident.owners[sid].current_worldbody_observation
                    is not cohort_probes[i]
                    for i, sid in enumerate(ids)
                )
            ):
                raise R23COriginalRejoinRequestHold("source changed before registration")
            # Reuse Original Owner's existing transient weak request registry.
            # Stage28 issuer requires type(CoverageAdoptionTurn), so this distinct
            # type does NOT become executable or adoption-eligible.
            resident._coverage_adoption_turns[turn.work_ref] = turn
            return turn
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            raise R23COriginalRejoinRequestHold(
                "original reJOIN Question request cannot be frozen"
            ) from exc


def compare_r23c_registered_l1_context(*, bridge,
                                      turn: R23CFrozenOriginalRejoinL1
                                      ) -> R23COriginalRejoinL1Comparison:
    """Revalidate ORIGINAL CPU registration and frozen request, without GPU."""
    if type(turn) is not R23CFrozenOriginalRejoinL1:
        raise R23COriginalRejoinRequestHold("original typed registered request required")
    resident = getattr(bridge, "cognitive_work", None)
    if resident is None:
        raise R23COriginalRejoinRequestHold("original Owner not found")
    with resident.lock:
        try:
            source = _original_source(bridge=bridge, self_id=turn.self_id)
            owner = resident.owners[turn.self_id]
            current_continuity = owner.retained.exploration_continuity
            current_revision = (
                0 if current_continuity is None else current_continuity.revision
            )
            if (
                resident._coverage_adoption_turns.get(turn.work_ref) is not turn
                or bridge.owners.get(turn.self_id) is not owner
                or owner is not turn.owner
                or source != turn.source
                or owner.retained is not turn.retained
                or owner.intent is not turn.intent_owner
                or owner.intent.events != turn.intent_events
                or current_revision != turn.continuity_revision
                or any(
                    resident.owners[sid] is not turn.cohort_owners[i]
                    or resident.current_scope(sid) != turn.cohort_scopes[i]
                    or resident.owners[sid].current_worldbody_observation
                    is not turn.cohort_probes[i]
                    for i, sid in enumerate(("A", "B"))
                )
                or turn.request.intent_id != (
                    None if owner.intent.current_intent is None
                    else owner.intent.current_intent.intent_id
                )
                or turn.request.identity_context != project_identity_context(
                    owner.retained.identity
                )
                or turn.request_sha256 != _digest(
                    source, turn.request, turn.cohort_scopes,
                )
                or turn.request.choices != CHOICES
                or turn.request.focus != source.original_inquiry.question_ref
                or turn.request.think_allowed
                or turn.model_invoked or turn.question_adopted
                or turn.intent_committed or turn.memory_written
                or turn.physical_authorized
            ):
                raise R23COriginalRejoinRequestHold(
                    "original Owner/request/Source or registration changed"
                )
            if (
                _original_source(bridge=bridge, self_id=turn.self_id) != source
                or resident._coverage_adoption_turns.get(turn.work_ref) is not turn
            ):
                raise R23COriginalRejoinRequestHold(
                    "source changed between CPU checks"
                )
            return R23COriginalRejoinL1Comparison(
                self_id=turn.self_id,
                request_id=turn.request.request_id,
                choice_ids=tuple(c.choice_id for c in turn.request.choices),
                question_ref=source.original_inquiry.question_ref,
                need_signal_ref=source.original_inquiry.need_signal_ref,
                schema_revision=source.current.schema.revision,
                source_revision_refs=source.current.source_revision_refs,
                request_sha256=turn.request_sha256,
                original_owner=owner,
            )
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            raise R23COriginalRejoinRequestHold(
                "registered original reJOIN request/current Context mismatch"
            ) from exc


def r23c_original_l1_request_is_live(*, bridge, turn: R23CFrozenOriginalRejoinL1) -> bool:
    """A cached request is never a model-ticket or Physical grant."""
    try:
        if not r23b_original_rejoin_inquiry_is_live(turn.source, bridge=bridge):
            return False
        compare_r23c_registered_l1_context(bridge=bridge, turn=turn)
        return True
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError):
        return False
