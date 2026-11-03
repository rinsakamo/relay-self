"""L-EU: immutable Experience–Understanding relation graph, shadow-only.

Experience records link to original source bytes via SHA256. Understandings are
versioned *interpretations*, not changes to the source or learned L1 state.
One experience may support many competing understandings, and a later
interpretation may revise an earlier one WITHOUT overwriting it.

No S10 learning commit, S11 Habit grant, PersistentCognition mutation,
S49 Action, provider HTTP or physical World is performed by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, replace

SCHEMA = "RELAY_EU_LEDGER_V1"
SHA = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
KIND = {"WORLD_OUTCOME", "MODEL_SELF_REVIEW", "OTHER_ATTESTED_SOURCE"}
STAGE = {"ORIGINAL_HYPOTHESIS", "POST_OUTCOME_REINTERPRETATION", "NEW_COMPETING_HYPOTHESIS"}
LINK = {"TESTED_BY", "INTERPRETS", "REVISES_ABOUT", "CONTRADICTED_BY", "MOTIVATES_REVIEW"}
REVIEW = {
    "UNTESTED",
    "ORIGINAL_PREDICTION_MISMATCH",
    "NUMERIC_LIMITED_SEMANTIC_FAIL",
    "PROPOSAL_NOT_ADMITTED",
    "UNRESOLVED",
}
SOURCE_STATUS = {"ARCHIVED_REPLAY_VERIFIED", "EXTERNAL_ATTESTATION_UNCONFIRMED"}
MAX_RECORDS = 128


class EUPairRejected(ValueError):
    """Invalid source-bound pair or an attempted implicit learning admission."""


def _id(field: str, value: object) -> None:
    if type(value) is not str or ID.fullmatch(value) is None:
        raise EUPairRejected(f"{field}: bounded ID required")


def _sha(field: str, value: object) -> None:
    if type(value) is not str or SHA.fullmatch(value) is None:
        raise EUPairRejected(f"{field}: exact lowercase SHA256 required")


def _text(field: str, value: object, *, limit: int = 1200) -> None:
    if type(value) is not str or not 0 < len(value.strip()) <= limit:
        raise EUPairRejected(f"{field}: bounded nonempty original text required")


def _parents(name: str, ids: object) -> None:
    if (
        type(ids) is not tuple or len(ids) > 16
        or any(type(x) is not str or ID.fullmatch(x) is None for x in ids)
        or len(set(ids)) != len(ids)
    ):
        raise EUPairRejected(f"{name}: unique bounded source IDs required")


def _one_of(name: str, value: object, options: set[str]) -> None:
    if type(value) is not str or value not in options:
        raise EUPairRejected(f"{name}: unsupported state")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise EUPairRejected("duplicate JSON field")
        obj[key] = value
    return obj


@dataclass(frozen=True, slots=True)
class Experience:
    """Original evidence reference, NOT a semantic interpretation."""

    experience_id: str
    source_sha256: str
    source_path: str
    source_kind: str
    source_status: str
    world_uuid: str | None
    fact_summary: str
    source_event: str

    def __post_init__(self) -> None:
        _id("experience_id", self.experience_id)
        _sha("experience source", self.source_sha256)
        _text("source_path", self.source_path, limit=512)
        if (
            self.source_path.startswith("/")
            or self.source_path.startswith("../")
            or "/../" in self.source_path
            or "\\" in self.source_path
        ):
            raise EUPairRejected("experience must use repo-relative original source")
        _one_of("source_kind", self.source_kind, KIND)
        _one_of("source_status", self.source_status, SOURCE_STATUS)
        if self.world_uuid is not None:
            _id("world_uuid", self.world_uuid)
        _text("fact_summary", self.fact_summary, limit=600)
        _text("source_event", self.source_event, limit=160)


@dataclass(frozen=True, slots=True)
class Understanding:
    """A model's immutable claim, possibly internally wrong, from raw text."""

    understanding_id: str
    stage: str
    original_response_sha256: str
    source_kind: str
    source_strategy: str
    original_decision: str
    original_speed_m_per_tick: float | None
    applicability: str
    reason_original: str
    falsification_original: str
    parent_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    epistemic_status: str = "UNADMITTED_MODEL_CLAIM"

    def __post_init__(self) -> None:
        _id("understanding_id", self.understanding_id)
        _one_of("stage", self.stage, STAGE)
        _sha("understanding original", self.original_response_sha256)
        _text("source_kind", self.source_kind, limit=64)
        for name in (
            "source_strategy", "original_decision", "applicability",
            "reason_original", "falsification_original",
        ):
            _text(name, getattr(self, name))
        # This is ORIGINAL model output, not a policy validator:
        # STATIONARY-vs-falsification or ABSTAIN-vs-approach inconsistencies
        # must remain representable instead of being silently repaired.
        speed = self.original_speed_m_per_tick
        if speed is not None and (
            type(speed) not in (float, int) or not math.isfinite(speed) or not 0 <= speed <= 0.3
        ):
            raise EUPairRejected("original speed must be bounded numeric or null")
        _parents("parent_ids", self.parent_ids)
        _parents("evidence_ids", self.evidence_ids)
        if not self.evidence_ids or self.understanding_id in self.parent_ids:
            raise EUPairRejected("understanding must cite evidence without self-revision")
        if self.epistemic_status != "UNADMITTED_MODEL_CLAIM":
            raise EUPairRejected("EU shadow may not self-qualify or learn")


@dataclass(frozen=True, slots=True)
class PairLink:
    """A review of one Experience ↔ Understanding pairing, not a truth claim."""

    experience_id: str
    understanding_id: str
    relation: str
    review: str
    review_source_sha256: str
    review_provenance: str
    reason: str

    def __post_init__(self) -> None:
        _id("experience_id", self.experience_id)
        _id("understanding_id", self.understanding_id)
        _one_of("relation", self.relation, LINK)
        _one_of("review", self.review, REVIEW)
        _sha("review source", self.review_source_sha256)
        _text("review_provenance", self.review_provenance, limit=100)
        _text("reason", self.reason, limit=800)


@dataclass(frozen=True, slots=True)
class EULedger:
    """Bounded immutable source graph. Append-only transitions, no admissions."""

    ledger_id: str
    experiences: tuple[Experience, ...] = ()
    understandings: tuple[Understanding, ...] = ()
    links: tuple[PairLink, ...] = ()
    memory_commits: int = 0
    action_authority: bool = False
    learning_admitted: bool = False
    habit_promotions: int = 0
    science_qualified: bool = False

    def __post_init__(self) -> None:
        _id("ledger_id", self.ledger_id)
        if (
            type(self.experiences) is not tuple
            or type(self.understandings) is not tuple
            or type(self.links) is not tuple
            or any(type(x) is not Experience for x in self.experiences)
            or any(type(x) is not Understanding for x in self.understandings)
            or any(type(x) is not PairLink for x in self.links)
            or max(len(self.experiences), len(self.understandings), len(self.links)) > MAX_RECORDS
        ):
            raise EUPairRejected("bounded typed immutable records required")
        if (
            type(self.memory_commits) is not int or self.memory_commits != 0
            or type(self.habit_promotions) is not int or self.habit_promotions != 0
            or self.action_authority is not False or self.learning_admitted is not False
            or self.science_qualified is not False
        ):
            raise EUPairRejected("shadow-only EU ledger cannot own learning/Action/qualification")
        evid = {}
        for e in self.experiences:
            if e.experience_id in evid:
                raise EUPairRejected("duplicate experience identity")
            evid[e.experience_id] = e
        prev: set[str] = set()
        for u in self.understandings:
            if u.understanding_id in prev:
                raise EUPairRejected("duplicate understanding/revision identity")
            if not set(u.parent_ids).issubset(prev):
                raise EUPairRejected("revision must point only to preceding immutable understanding")
            if not set(u.evidence_ids).issubset(evid):
                raise EUPairRejected("understanding cites missing original experience")
            if u.stage == "ORIGINAL_HYPOTHESIS" and u.parent_ids:
                raise EUPairRejected("H1 may not have an implicit predecessor")
            if u.stage != "ORIGINAL_HYPOTHESIS" and not u.parent_ids:
                raise EUPairRejected("reassessment must cite its original hypothesis")
            prev.add(u.understanding_id)
        seen = set()
        for link in self.links:
            key = (link.experience_id, link.understanding_id, link.relation)
            if key in seen:
                raise EUPairRejected("duplicate pair-relation identity")
            seen.add(key)
            if link.experience_id not in evid or link.understanding_id not in prev:
                raise EUPairRejected("unbound pair-relation endpoint")
            bound = next(u for u in self.understandings if u.understanding_id == link.understanding_id)
            if link.experience_id not in bound.evidence_ids:
                raise EUPairRejected("interpretation link absent from original evidence citations")

    def add_experience(self, value: Experience) -> EULedger:
        if type(value) is not Experience:
            raise EUPairRejected("typed experience required")
        return replace(self, experiences=(*self.experiences, value))

    def add_understanding(self, value: Understanding) -> EULedger:
        if type(value) is not Understanding:
            raise EUPairRejected("typed original understanding required")
        return replace(self, understandings=(*self.understandings, value))

    def link(self, value: PairLink) -> EULedger:
        if type(value) is not PairLink:
            raise EUPairRejected("typed relation required")
        return replace(self, links=(*self.links, value))

    def interpretations_for(self, experience_id: str) -> tuple[Understanding, ...]:
        """Return ALL claims, including rejected H2 and competing branches."""
        _id("experience_id", experience_id)
        if all(e.experience_id != experience_id for e in self.experiences):
            raise EUPairRejected("unknown original experience")
        return tuple(u for u in self.understandings if experience_id in u.evidence_ids)


def encode_ledger(ledger: EULedger) -> bytes:
    if type(ledger) is not EULedger:
        raise EUPairRejected("typed immutable ledger required")
    payload = {"schema": SCHEMA, "ledger": asdict(ledger)}
    return canonical({
        "schema": SCHEMA,
        "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest(),
        "payload": payload,
    }) + b"\n"


def decode_ledger(raw: bytes) -> EULedger:
    if type(raw) is not bytes or not raw.endswith(b"\n") or len(raw) > 512_000:
        raise EUPairRejected("bounded exact newline-terminated EU original required")
    try:
        env = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        if (
            type(env) is not dict or set(env) != {"schema", "payload_sha256", "payload"}
            or env["schema"] != SCHEMA or type(env["payload"]) is not dict
            or set(env["payload"]) != {"schema", "ledger"}
            or env["payload"]["schema"] != SCHEMA
            or hashlib.sha256(canonical(env["payload"])).hexdigest() != env["payload_sha256"]
        ):
            raise EUPairRejected("invalid EU schema/content digest")
        data = env["payload"]["ledger"]
        if type(data) is not dict or set(data) != set(EULedger.__dataclass_fields__):
            raise EUPairRejected("exact ledger schema required")
        def decoded(items: object, cls: type):
            if type(items) is not list or len(items) > MAX_RECORDS:
                raise EUPairRejected("bounded original records array required")
            fields = set(cls.__dataclass_fields__)
            if any(type(x) is not dict or set(x) != fields for x in items):
                raise EUPairRejected("exact typed EU record fields required")
            return tuple(cls(**{
                **v,
                **({"parent_ids": tuple(v["parent_ids"]), "evidence_ids": tuple(v["evidence_ids"])}
                   if cls is Understanding else {}),
            }) for v in items)
        ledger = EULedger(
            ledger_id=data["ledger_id"],
            experiences=decoded(data["experiences"], Experience),
            understandings=decoded(data["understandings"], Understanding),
            links=decoded(data["links"], PairLink),
            memory_commits=data["memory_commits"],
            action_authority=data["action_authority"],
            learning_admitted=data["learning_admitted"],
            habit_promotions=data["habit_promotions"],
            science_qualified=data["science_qualified"],
        )
        if encode_ledger(ledger) != raw:
            raise EUPairRejected("noncanonical/replayed EU ledger bytes")
        return ledger
    except (UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise EUPairRejected("invalid EU original envelope/record") from exc
