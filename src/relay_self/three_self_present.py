"""3Self / Present / Memory v0.1 owner-neutral read-only contract (Issue #833).

No independent SelfModel/WorldModel/BodyModel DB, Goal owner, Action issuer,
Memory mutation, inference backend, or source attestation is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.common_io import ScopeRef
from relay_self.innate_schema import (
    CognitiveSignal,
    SchemaSnapshot,
    signal_is_current,
)
from relay_self.persistent_cognition import PersistentCognition
from relay_self.provenance import Provenance


class PresentContractError(ValueError):
    """Invalid, ambiguous or stale self-lens/present boundary input."""


class Lens(str, Enum):
    MYSELF = "MYSELF"
    SELF_WORLD = "SELF_WORLD"
    SELF_BODY = "SELF_BODY"


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    REMEMBERED = "REMEMBERED"
    INFERRED = "INFERRED"
    PREDICTED = "PREDICTED"
    HYPOTHETICAL = "HYPOTHETICAL"
    UNKNOWN = "UNKNOWN"


class QuestionDisposition(str, Enum):
    ADOPT = "ADOPT"
    HOLD = "HOLD"
    DECLINE = "DECLINE"


@dataclass(frozen=True, slots=True)
class LensClaim:
    """Reference to one bounded claim, not a new semantic fact or mutable store."""

    scope: ScopeRef
    lens: Lens
    claim_key: str
    status: EpistemicStatus
    source_refs: tuple[Provenance, ...] = ()
    source_revision_refs: tuple[str, ...] = ()
    value_ref: str | None = None
    coverage_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not isinstance(self.lens, Lens):
            raise PresentContractError("lens claim requires valid scope and lens")
        _text("claim_key", self.claim_key)
        if not isinstance(self.status, EpistemicStatus):
            raise PresentContractError("invalid epistemic status")
        _provenance_refs(self.source_refs)
        _refs("source_revision_refs", self.source_revision_refs)
        if self.status is EpistemicStatus.UNKNOWN:
            if self.source_revision_refs or self.value_ref is not None:
                raise PresentContractError("UNKNOWN may not carry a known value/revision")
        else:
            if not self.source_refs:
                raise PresentContractError("qualified claim requires source provenance")
            _text("value_ref", self.value_ref)
        if self.status is EpistemicStatus.OBSERVED:
            if self.scope.world_session_id is None or not self.source_revision_refs:
                raise PresentContractError("OBSERVED needs World session and current source")
        if self.coverage_ref is not None:
            _text("coverage_ref", self.coverage_ref)


@dataclass(frozen=True, slots=True)
class LensView:
    scope: ScopeRef
    epoch_ref: str
    lens: Lens
    source_revision_refs: tuple[str, ...]
    claims: tuple[LensClaim, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not isinstance(self.lens, Lens):
            raise PresentContractError("invalid lens view scope/type")
        _text("epoch_ref", self.epoch_ref)
        _refs("source_revision_refs", self.source_revision_refs)
        if not isinstance(self.claims, tuple):
            raise PresentContractError("lens claims must be tuple")
        keys: set[str] = set()
        for claim in self.claims:
            if not isinstance(claim, LensClaim):
                raise PresentContractError("lens claims must be typed")
            if claim.scope != self.scope or claim.lens is not self.lens:
                raise PresentContractError("foreign scope or lens in view")
            if claim.claim_key in keys:
                raise PresentContractError("duplicate lens claim")
            keys.add(claim.claim_key)
            if (
                claim.status is EpistemicStatus.OBSERVED
                and claim.source_revision_refs != self.source_revision_refs
            ):
                raise PresentContractError("stale observation cannot be current OBSERVED")

    def read(self, claim_key: str) -> LensClaim:
        _text("claim_key", claim_key)
        for claim in self.claims:
            if claim.claim_key == claim_key:
                return claim
        # Unobserved is UNKNOWN, not False, 0 or verified absent.
        return LensClaim(
            scope=self.scope, lens=self.lens,
            claim_key=claim_key, status=EpistemicStatus.UNKNOWN,
        )


@dataclass(frozen=True, slots=True)
class ThreeSelfProjection:
    """One Self with three read-only lenses of common qualified owner evidence."""

    scope: ScopeRef
    epoch_ref: str
    source_revision_refs: tuple[str, ...]
    identity_provenance: Provenance
    my_self: LensView
    self_world: LensView
    self_body: LensView

    def __post_init__(self) -> None:
        _text("epoch_ref", self.epoch_ref)
        _refs("source_revision_refs", self.source_revision_refs)
        if not isinstance(self.identity_provenance, Provenance):
            raise PresentContractError("identity requires existing provenance")
        for lens, view in (
            (Lens.MYSELF, self.my_self),
            (Lens.SELF_WORLD, self.self_world),
            (Lens.SELF_BODY, self.self_body),
        ):
            if (
                not isinstance(view, LensView)
                or view.lens is not lens
                or view.scope != self.scope
                or view.epoch_ref != self.epoch_ref
                or view.source_revision_refs != self.source_revision_refs
            ):
                raise PresentContractError("3Self must share scope, epoch and sources")


def project_three_self(
    *,
    retained: PersistentCognition,
    scope: ScopeRef,
    epoch_ref: str,
    source_revision_refs: tuple[str, ...],
    claims: tuple[LensClaim, ...] = (),
    memory_lens_refs: tuple[tuple[Lens, str], ...] = (),
) -> ThreeSelfProjection:
    """Compose read-only references; do not rematerialize WB Draft #634 views.

    Native inputs and owner qualified WB readings must be supplied by the caller.
    Memory is selected explicitly and always tagged REMEMBERED.
    """
    if not isinstance(retained, PersistentCognition):
        raise PresentContractError("retained must be existing PersistentCognition")
    if retained.identity.self_id != scope.self_id:
        raise PresentContractError("foreign retained cognition self")
    _text("epoch_ref", epoch_ref)
    _refs("source_revision_refs", source_revision_refs)
    if not isinstance(claims, tuple) or not all(isinstance(c, LensClaim) for c in claims):
        raise PresentContractError("claims must be LensClaim tuple")
    if not isinstance(memory_lens_refs, tuple):
        raise PresentContractError("memory_lens_refs must be tuple")

    entries = list(claims)
    for claim in claims:
        if claim.scope != scope:
            raise PresentContractError("foreign Self/World session claim")

    memories = {m.memory_id: m for m in retained.memories}
    for selection in memory_lens_refs:
        if (
            not isinstance(selection, tuple) or len(selection) != 2
            or not isinstance(selection[0], Lens) or not isinstance(selection[1], str)
        ):
            raise PresentContractError("invalid memory lens selection")
        lens, memory_id = selection
        if memory_id not in memories:
            raise PresentContractError("memory not held by retained owner")
        memory = memories[memory_id]
        entries.append(
            LensClaim(
                scope=scope, lens=lens, claim_key=f"memory:{memory_id}",
                status=EpistemicStatus.REMEMBERED,
                source_refs=(memory.source_provenance, memory.integration_provenance),
                value_ref=memory_id,
            )
        )

    def view(lens: Lens) -> LensView:
        return LensView(
            scope=scope, epoch_ref=epoch_ref, lens=lens,
            source_revision_refs=source_revision_refs,
            claims=tuple(c for c in entries if c.lens is lens),
        )

    return ThreeSelfProjection(
        scope=scope, epoch_ref=epoch_ref,
        source_revision_refs=source_revision_refs,
        identity_provenance=retained.identity.provenance,
        my_self=view(Lens.MYSELF),
        self_world=view(Lens.SELF_WORLD),
        self_body=view(Lens.SELF_BODY),
    )


@dataclass(frozen=True, slots=True)
class PresentFrame:
    """Transient Self projection; caller supplies existing active owner refs."""

    three_self: ThreeSelfProjection
    frame_revision: int
    registry_revision: int
    signals: tuple[CognitiveSignal, ...]
    attention_refs: tuple[str, ...] = ()
    need_refs: tuple[str, ...] = ()
    active_question_refs: tuple[str, ...] = ()
    active_goal_refs: tuple[str, ...] = ()
    active_intent_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.three_self, ThreeSelfProjection):
            raise PresentContractError("Present requires 3Self projection")
        _nonnegative("frame_revision", self.frame_revision)
        _nonnegative("registry_revision", self.registry_revision)
        if not isinstance(self.signals, tuple) or not all(
            isinstance(s, CognitiveSignal) for s in self.signals
        ):
            raise PresentContractError("signals must be CognitiveSignal tuple")
        if len({s.envelope.event_id for s in self.signals}) != len(self.signals):
            raise PresentContractError("duplicate signal event")
        for key in ("attention_refs", "need_refs", "active_question_refs",
                    "active_goal_refs", "active_intent_refs"):
            _refs(key, getattr(self, key))


def project_present_frame(
    *,
    three_self: ThreeSelfProjection,
    snapshot: SchemaSnapshot,
    current_registry_revision: int,
    current_source_revision_refs: tuple[str, ...],
    frame_revision: int,
    signals: tuple[CognitiveSignal, ...] = (),
    attention_refs: tuple[str, ...] = (),
    need_refs: tuple[str, ...] = (),
    active_question_refs: tuple[str, ...] = (),
    active_goal_refs: tuple[str, ...] = (),
    active_intent_refs: tuple[str, ...] = (),
) -> PresentFrame:
    """Derive one Present from owner-supplied refs without any lifecycle mutation."""
    if three_self.scope.self_id != snapshot.self_id:
        raise PresentContractError("3Self/Schema Self mismatch")
    if three_self.source_revision_refs != current_source_revision_refs:
        raise PresentContractError("stale 3Self source")
    if snapshot.revision != current_registry_revision:
        raise PresentContractError("stale schema registry revision")
    for signal in signals:
        if not signal_is_current(
            signal, snapshot=snapshot, scope=three_self.scope,
            source_revision_refs=current_source_revision_refs,
            requested_mode=signal.execution_mode,
            current_registry_revision=current_registry_revision,
        ):
            raise PresentContractError("unqualified/stale Schema signal")
    return PresentFrame(
        three_self=three_self,
        frame_revision=frame_revision,
        registry_revision=snapshot.revision,
        signals=signals,
        attention_refs=attention_refs,
        need_refs=need_refs,
        active_question_refs=active_question_refs,
        active_goal_refs=active_goal_refs,
        active_intent_refs=active_intent_refs,
    )


@dataclass(frozen=True, slots=True)
class QuestionDecisionReceipt:
    """Owner-supplied decision trace, NOT a committed Question/Goal/Intent."""

    signal_event_id: str
    scope: ScopeRef
    frame_revision: int
    registry_revision: int
    owner_revision: int
    disposition: QuestionDisposition
    provenance: Provenance

    def __post_init__(self) -> None:
        _text("signal_event_id", self.signal_event_id)
        _nonnegative("frame_revision", self.frame_revision)
        _nonnegative("registry_revision", self.registry_revision)
        _nonnegative("owner_revision", self.owner_revision)
        if not isinstance(self.scope, ScopeRef):
            raise PresentContractError("invalid receipt scope")
        if not isinstance(self.disposition, QuestionDisposition):
            raise PresentContractError("invalid question disposition")
        if not isinstance(self.provenance, Provenance):
            raise PresentContractError("decision needs owner provenance")


def review_question_candidate(
    *,
    present: PresentFrame,
    snapshot: SchemaSnapshot,
    signal_event_id: str,
    disposition: QuestionDisposition,
    owner_self_id: str,
    expected_owner_revision: int,
    current_owner_revision: int,
    current_frame_revision: int,
    current_registry_revision: int,
    current_source_revision_refs: tuple[str, ...],
    provenance: Provenance,
) -> QuestionDecisionReceipt:
    """Validate the *Self owner's* chosen disposition; do not select it for Self."""
    _text("owner_self_id", owner_self_id)
    _text("signal_event_id", signal_event_id)
    _nonnegative("expected_owner_revision", expected_owner_revision)
    _nonnegative("current_owner_revision", current_owner_revision)
    if owner_self_id != present.three_self.scope.self_id:
        raise PresentContractError("foreign Self decision owner")
    if expected_owner_revision != current_owner_revision:
        raise PresentContractError("stale Self owner revision")
    if present.frame_revision != current_frame_revision:
        raise PresentContractError("stale Present frame")
    if present.registry_revision != current_registry_revision:
        raise PresentContractError("stale Present registry")
    if present.three_self.source_revision_refs != current_source_revision_refs:
        raise PresentContractError("stale Present source")
    matched = tuple(s for s in present.signals if s.envelope.event_id == signal_event_id)
    if len(matched) != 1 or matched[0].signal_kind != "QUESTION_CANDIDATE":
        raise PresentContractError("unknown or non-Question signal")
    signal = matched[0]
    if not signal_is_current(
        signal, snapshot=snapshot, scope=present.three_self.scope,
        source_revision_refs=current_source_revision_refs,
        requested_mode=signal.execution_mode,
        current_registry_revision=current_registry_revision,
    ):
        raise PresentContractError("stale Schema candidate")
    return QuestionDecisionReceipt(
        signal_event_id=signal_event_id,
        scope=present.three_self.scope,
        frame_revision=present.frame_revision,
        registry_revision=present.registry_revision,
        owner_revision=current_owner_revision,
        disposition=disposition,
        provenance=provenance,
    )


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PresentContractError(f"{name} must be non-empty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PresentContractError(f"{name} must be non-negative integer")


def _refs(name: str, refs: object) -> None:
    if not isinstance(refs, tuple):
        raise PresentContractError(f"{name} must be tuple")
    for ref in refs:
        _text(name, ref)
    if len(set(refs)) != len(refs):
        raise PresentContractError(f"{name} contains duplicate entries")


def _provenance_refs(refs: object) -> None:
    if not isinstance(refs, tuple) or not all(isinstance(r, Provenance) for r in refs):
        raise PresentContractError("source_refs must be existing Provenance tuple")
