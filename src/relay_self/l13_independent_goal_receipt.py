"""L13: prospective independent Goal receipt -> L10 previous-epoch candidate.

Three original byte sources, distinct independent S/R/V admissions and
existing S16 Action are REQUIRED. SHA membership and typed owner strings are
NOT cryptographic proof of real Minecraft/Goal provenance. Never use an
eventual World-level Goal summary as a per-Action reward. No new World I/O.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    parse_mineflayer_line,
)
from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat
from relay_self.action import ActionLifecycle
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.experience_bridge import QualifiedEpisode, qualify_episode
from relay_self.habit_shadow import ExternalGoalLabel, GoalSourceAdmission
from relay_self.l10_world_body_cue_learning import (
    PriorWorldBodyEpisode,
    WorldBodyCueWitness,
    project_admitted_world_body_cues,
)
from relay_self.provenance import Provenance
from relay_self.self_body import SelfBodyView
from relay_self.self_world import SelfWorldView

_PRE_SCHEMA = "L13_S16_TERMINAL_SOURCE_V1"
_GOAL_SCHEMA = "L13_EXTERNAL_PER_ACTION_GOAL_V1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MAX = 65536
_ACTION_KEYS = frozenset({
    "schema", "session_id", "action_id", "binding_id", "action_ref",
    "pre_probe_sha256", "before_seq", "after_seq", "source_revision",
    "source_status", "disposition", "reason_code", "world_source",
    "world_reference",
})
_GOAL_KEYS = frozenset({
    "schema", "session_id", "action_id", "source_action_sha256",
    "source_pre_probe_sha256", "action_end_seq", "goal_observed_seq",
    "goal_status", "criterion_id", "external_goal_owner_ref",
    "no_intervening_action_attested",
})


class L13ReceiptRejected(ValueError):
    """No receipt, mixed source, unadmitted digest or retrospective reward."""


class L13ReceiptStatus(str, Enum):
    SOURCE_SHAPED_GOAL_CANDIDATE = "source_shaped_external_goal_candidate"
    UNKNOWN_NO_GOAL_LABEL = "unknown_goal_result_no_label"
    ARCHIVED_G413_NO_ACTION_GOAL = "archived_g413_no_per_action_goal_source"


@dataclass(frozen=True, slots=True)
class L13IndependentSourceAdmission:
    """S/R/V-owner supplied external admission; NOT itself a proof/signature.

    Three distinct owners and exact SHA membership are prerequisites. A
    caller cannot use L13 to attest the contents' real-world authenticity.
    """

    admitted_present_sha256: frozenset[str]
    admitted_action_sha256: frozenset[str]
    admitted_goal_sha256: frozenset[str]
    present_owner: str
    action_owner: str
    goal_owner: str
    review_provenance: Provenance

    def __post_init__(self) -> None:
        for name in (
            "admitted_present_sha256", "admitted_action_sha256",
            "admitted_goal_sha256",
        ):
            digests = getattr(self, name)
            if (
                not isinstance(digests, frozenset)
                or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
                       for x in digests)
            ):
                raise L13ReceiptRejected("independent owner must admit exact original SHA")
        owners = (self.present_owner, self.action_owner, self.goal_owner)
        if (
            any(not isinstance(x, str) or not x.strip() for x in owners)
            or len(set(owners)) != 3
            or not isinstance(self.review_provenance, Provenance)
            or self.review_provenance.source in owners
        ):
            raise L13ReceiptRejected("three distinct owners and separate S/R/V review required")


@dataclass(frozen=True, slots=True)
class L13ReceiptTriplet:
    """Read-only original-byte inputs plus already-typed existing S/L owners."""

    native: NativeThreat
    world: SelfWorldView
    body: SelfBodyView
    action: ActionLifecycle
    outcome: ActionOutcomeInterpretation
    raw_native_probe: bytes
    raw_s16_action: bytes
    raw_external_goal: bytes
    self_id: str
    source_revision: int


@dataclass(frozen=True, slots=True)
class L13ReadOnlyReview:
    status: L13ReceiptStatus
    source_present_sha256: str
    source_action_sha256: str
    source_goal_sha256: str
    witness: WorldBodyCueWitness | None
    qualified_episode: QualifiedEpisode | None
    goal_label: ExternalGoalLabel | None
    prior_l10: PriorWorldBodyEpisode | None
    goal_source_admission: GoalSourceAdmission | None
    per_action_goal_source_candidate_count: int
    # Neither typed input nor an independently asserted SHA set is a physical
    # authentication or a causal claim. External S/R/V must review original.
    real_original_authenticated_by_l13: bool = False
    goal_improvement_attested: bool = False
    action_authority: bool = False
    s10_learning_updates: int = 0
    s11_habit_grants: int = 0
    world_reads: int = 0
    new_actions: int = 0


def _no_duplicate_json_keys(items: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for name, value in items:
        if name in result:
            raise L13ReceiptRejected("duplicate original JSON field")
        result[name] = value
    return result


def _raw(raw: bytes, label: str) -> tuple[dict, str]:
    if (
        not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX
        or not raw.endswith(b"\n") or raw.count(b"\n") != 1
    ):
        raise L13ReceiptRejected(f"{label}: one bounded original JSONL line required")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_json_keys)
    except (UnicodeError, ValueError) as exc:
        raise L13ReceiptRejected(f"{label}: bad JSON/UTF-8 original") from exc
    if not isinstance(data, dict):
        raise L13ReceiptRejected(f"{label}: original must be JSON object")
    return data, hashlib.sha256(raw).hexdigest()


def _source(schema: str, data: dict, exact: frozenset[str]) -> None:
    if set(data) != exact or data.get("schema") != schema:
        raise L13ReceiptRejected("unknown source envelope, injection or missing field")


def join_independent_action_goal_source(
    item: L13ReceiptTriplet, admission: L13IndependentSourceAdmission,
    *, current: WorldBodyCueWitness,
) -> L13ReadOnlyReview:
    """Prepare a next-epoch L10 *candidate*, never physically attest it.

    L13 has no authority to read a World or create an external reviewer's
    original bytes. The external Goal contract is *prospective*: a fabricated
    copy of the report is not a real original. S/R/V must independently check
    the producer, exact original bytes, nonintervention and goal criterion.
    """
    if (
        not isinstance(item, L13ReceiptTriplet)
        or not isinstance(admission, L13IndependentSourceAdmission)
        or not isinstance(current, WorldBodyCueWitness)
        or type(item.source_revision) is not int or item.source_revision < 0
        or not isinstance(item.self_id, str) or not item.self_id
        or not isinstance(item.action, ActionLifecycle)
        or not isinstance(item.outcome, ActionOutcomeInterpretation)
    ):
        raise L13ReceiptRejected("typed distinct previous and current owner required")
    native_data, native_sha = _raw(item.raw_native_probe, "native Present")
    action_data, action_sha = _raw(item.raw_s16_action, "S16 Action")
    goal_data, goal_sha = _raw(item.raw_external_goal, "external Goal")
    _source(_PRE_SCHEMA, action_data, _ACTION_KEYS)
    _source(_GOAL_SCHEMA, goal_data, _GOAL_KEYS)
    if (
        len({native_sha, action_sha, goal_sha}) != 3
        or native_sha not in admission.admitted_present_sha256
        or action_sha not in admission.admitted_action_sha256
        or goal_sha not in admission.admitted_goal_sha256
    ):
        raise L13ReceiptRejected("mixed/missing external source SHA admission")
    if native_data.get("type") != "observation":
        raise L13ReceiptRejected("pre-Action must be native observation, not belief")
    try:
        parsed = parse_mineflayer_line(item.raw_native_probe.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise L13ReceiptRejected("native original not valid typed Mineflayer Present") from exc
    if (
        not isinstance(parsed, MineflayerObservation)
        or not isinstance(item.native, NativeThreat)
        or parsed != item.native.observation or parsed.kind != "probe"
        or item.self_id != current.self_id
        or parsed.session_id == current.session_id
        or item.source_revision >= current.source_revision
    ):
        raise L13ReceiptRejected("source Present/epoch mismatch or future leakage")
    witness = project_admitted_world_body_cues(
        native=item.native, world=item.world, body=item.body,
        owner_self_id=item.self_id,
        source_revision=item.source_revision,
        original_probe_sha256=native_sha,
        admitted_probe_sha256=admission.admitted_present_sha256,
    )
    outcome = item.outcome
    if (
        not item.action.is_current_snapshot
        or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
        or outcome.source_status != "executed"
        or item.action.action_id != outcome.action_id
        or witness.session_id != outcome.session_id
        or action_data["session_id"] != witness.session_id
        or action_data["action_id"] != outcome.action_id
        or action_data["binding_id"] != outcome.binding_id
        or action_data["action_ref"] != outcome.action_ref
        or action_data["pre_probe_sha256"] != native_sha
        or action_data["before_seq"] != witness.native_seq
        or type(action_data["before_seq"]) is not int
        or type(action_data["after_seq"]) is not int
        or action_data["after_seq"] <= action_data["before_seq"]
        or type(action_data["source_revision"]) is not int
        or action_data["source_revision"] != witness.source_revision
        or action_data["source_status"] != outcome.source_status
        or action_data["disposition"] != outcome.disposition.value
        or action_data["reason_code"] != outcome.reason_code
        or action_data["world_source"] != outcome.world_provenance.source
        or action_data["world_reference"] != outcome.world_provenance.reference
    ):
        raise L13ReceiptRejected("Action/S16 original source is not same terminal")
    if (
        goal_data["session_id"] != witness.session_id
        or goal_data["action_id"] != outcome.action_id
        or goal_data["source_action_sha256"] != action_sha
        or goal_data["source_pre_probe_sha256"] != native_sha
        or goal_data["action_end_seq"] != action_data["after_seq"]
        or type(goal_data["action_end_seq"]) is not int
        or type(goal_data["goal_observed_seq"]) is not int
        or goal_data["goal_observed_seq"] <= goal_data["action_end_seq"]
        or not isinstance(goal_data["criterion_id"], str)
        or not goal_data["criterion_id"].strip()
        or goal_data["external_goal_owner_ref"] != admission.goal_owner
        or goal_data["no_intervening_action_attested"] is not True
        or goal_data["goal_status"] not in (
            "REACHED", "NOT_REACHED", "UNDETERMINED",
        )
    ):
        raise L13ReceiptRejected("external Goal original/Action causal window unverified")
    qualified = qualify_episode(
        item.action, outcome, world_revision=witness.source_revision,
        evidence_sha256=action_sha, cue_tags=witness.cue_tags,
    )
    # UNKNOWN is not False: do not construct an ExternalGoalLabel.
    if goal_data["goal_status"] == "UNDETERMINED":
        return L13ReadOnlyReview(
            status=L13ReceiptStatus.UNKNOWN_NO_GOAL_LABEL,
            source_present_sha256=native_sha,
            source_action_sha256=action_sha, source_goal_sha256=goal_sha,
            witness=witness, qualified_episode=qualified, goal_label=None,
            prior_l10=None, goal_source_admission=None,
            per_action_goal_source_candidate_count=0,
        )
    goal = ExternalGoalLabel(
        qualified.episode.memory_id, goal_sha,
        goal_data["goal_status"] == "REACHED",
        Provenance("external-goal-claimed", admission.goal_owner),
    )
    return L13ReadOnlyReview(
        status=L13ReceiptStatus.SOURCE_SHAPED_GOAL_CANDIDATE,
        source_present_sha256=native_sha,
        source_action_sha256=action_sha, source_goal_sha256=goal_sha,
        witness=witness, qualified_episode=qualified,
        goal_label=goal,
        prior_l10=PriorWorldBodyEpisode(
            item.native, item.world, item.body, witness, qualified, goal,
        ),
        goal_source_admission=GoalSourceAdmission(
            frozenset({action_sha}), frozenset({goal_sha}),
        ),
        per_action_goal_source_candidate_count=1,
    )


def review_l12_g413_archive_no_per_action_goal(
    archived_l12: object,
) -> L13ReadOnlyReview:
    """Sourced L12 G413 endpoint metrics are never individual Goal originals."""
    from adapters.mineflayer.l12_archived_action_progress_no_reward_dev import (
        L12GoalTrainingGate,
    )

    if (
        not isinstance(archived_l12, L12GoalTrainingGate)
        or archived_l12.classification !=
            "L12_REAL_S49_ENDPOINT_PROGRESS_ONLY_NO_PER_ACTION_GOAL_TRAINING"
        or archived_l12.independent_per_action_goal_receipts != 0
        or archived_l12.qualified_l10_training_pairs != 0
        or archived_l12.original_native_pre_action_world_body_receipts != 0
        or any(x.external_action_goal_reached is not None
               or x.per_action_goal_attested for x in archived_l12.action_progress)
    ):
        raise L13ReceiptRejected("archived World-level Goal cannot be individual Goal")
    return L13ReadOnlyReview(
        status=L13ReceiptStatus.ARCHIVED_G413_NO_ACTION_GOAL,
        source_present_sha256="", source_action_sha256="",
        source_goal_sha256="", witness=None, qualified_episode=None,
        goal_label=None, prior_l10=None, goal_source_admission=None,
        per_action_goal_source_candidate_count=0,
    )
