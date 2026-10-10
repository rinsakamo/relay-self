"""I1: execute existing S29/S27/S24/S19/S11 and mainline Memory READ contracts.

This experiment-local seam never changes an owner, issues Actions, creates a
LearningFeedback, grants a Habit, schedules L2, or authenticates real Minecraft.
The S24 reference is *already evaluated* by the explicit caller: matching it
with cheap S11 selection is NOT a demonstrated saving of that evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.correlated_probe import CorrelatedProbeReceipt
from relay_self.epoch_continuation import read_retained_preference
from relay_self.execution_admission import AdmissionDecisionStatus
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.persistent_cognition import PersistentCognition
from relay_self.postfailure_cognition import PostFailureEpochTrace
from relay_self.provenance import Provenance
from relay_self.source_native_world import SourceNativeThreatReceipt

VERSION = "AC-INTEGRATION-I1-S29-OWNER-READONLY-v1"
MANIFEST_SHA256 = "5007043587580a3e6c9d23023bcc618582f3468b897e8ded8707b434ca87a06f"
MANIFEST_PATH = Path(__file__).with_name("ac_integration_i1_manifest.json")
STAGE_IDS = (
    "s24-att", "s24-blf", "s24-cnc", "s24-prd-wait",
    "s24-prd-move", "s24-plan", "s24-route", "s24-admit",
)


class I1OwnerSeamRejected(ValueError):
    """Unqualified current-source or owner contract: nothing was committed."""


@dataclass(frozen=True, slots=True)
class I1ReadOnlyResult:
    source_request_id: str
    source_session: str
    source_seq: int
    evidence_id: str
    retained_revision: int
    memory_id: str
    habit_status: str
    habit_candidate: str | None
    reference_candidate: str
    allocation_decision: str
    requires_l2_candidate: bool
    action_authorized: bool = False
    learning_committed: bool = False
    physical_source_attested: bool = False
    production_go: bool = False


def manifest_digest(raw: str) -> str:
    obj = json.loads(raw, object_pairs_hook=_unique_pairs)
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise I1OwnerSeamRejected("duplicate manifest JSON key")
        result[key] = value
    return result


def verify_frozen_manifest(raw: str | None = None) -> None:
    if raw is None:
        raw = MANIFEST_PATH.read_text(encoding="utf-8")
    if manifest_digest(raw) != MANIFEST_SHA256:
        raise I1OwnerSeamRejected("I1 frozen manifest digest drift")


def read_i1_owner_seam(
    owner_receipt: CorrelatedProbeReceipt,
    supplied_receipt: CorrelatedProbeReceipt,
    trace: PostFailureEpochTrace,
    supervisor: ActionSupervisor,
    action3: ActionLifecycle,
    consequence3: WorldConsequence,
    intent: IntentCommitment,
    current_retained: LearningPreferenceState,
    supplied_retained: LearningPreferenceState,
    cognition: PersistentCognition,
    memory_id: str,
    repertoire: HabitRepertoire,
    *,
    provenance: Provenance,
) -> I1ReadOnlyResult:
    """One explicit caller's non-authoritative S29 -> MEM/S11/S19/S24 comparison.

    `owner_receipt` and `current_retained` are caller-designated exact
    current objects. This checks their identity but cannot independently prove
    that caller designated the genuine physical source or owner root.
    """
    if (
        not isinstance(owner_receipt, CorrelatedProbeReceipt)
        or not isinstance(supplied_receipt, CorrelatedProbeReceipt)
        or supplied_receipt is not owner_receipt
    ):
        raise I1OwnerSeamRejected("receipt is not exact caller-current S29 object")
    if not isinstance(trace, PostFailureEpochTrace):
        raise I1OwnerSeamRejected("S24 trace must be typed and caller-executed")
    if (
        not isinstance(supervisor, ActionSupervisor)
        or not isinstance(action3, ActionLifecycle)
        or action3.state is not ActionState.OUTCOME
        or not action3.is_current_snapshot
        or supervisor.get(action3.action_id) is not action3
        or supervisor.open_actions
    ):
        raise I1OwnerSeamRejected("not current terminal S23 Action owner")
    if (
        not isinstance(consequence3, WorldConsequence)
        or consequence3.status is not WorldConsequenceStatus.EXECUTED
        or consequence3.action_id != action3.action_id
        or consequence3.provenance != action3.events[-1].provenance
    ):
        raise I1OwnerSeamRejected("unknown or mismatched World consequence")
    if not isinstance(intent, IntentCommitment):
        raise I1OwnerSeamRejected("requires existing IntentCommitment owner")
    current_intent = intent.current_intent
    if (
        current_intent is None
        or intent.pending_reconsideration is not None
        or current_intent.intent_id != action3.intent_id
    ):
        raise I1OwnerSeamRejected("wrong or reconsidering current Intent")
    if not isinstance(provenance, Provenance):
        raise I1OwnerSeamRejected("read provenance is not typed")

    r = supplied_receipt
    s = r.source_receipt
    if not isinstance(s, SourceNativeThreatReceipt):
        raise I1OwnerSeamRejected("requires existing S27 source projection")
    obs = s.source
    evidence = s.evidence
    if consequence3.after_observation is None:
        raise I1OwnerSeamRejected("missing original terminal World observation")
    if (
        r.request_id != "s29-probe:one.1"
        or r.request_id != r.acknowledged_request_id
        or obs.request_id != r.request_id
        or obs.session_id != consequence3.session_id
        or obs.kind != "probe"
        or obs.seq != r.probe_seq
        or r.request_cursor_seq != s.parent_after_seq + 1
        or r.next_cursor_seq != r.probe_seq + 1
        or r.received_count != 1
        or s.parent_after_seq != consequence3.after_observation.seq
        or r.inspected_at_ns != s.inspected_at_ns
        or trace.world_evidence is not evidence
        or evidence.action_id != action3.action_id
        or evidence.session_id != consequence3.session_id
        or evidence.consequence_provenance != consequence3.provenance
    ):
        raise I1OwnerSeamRejected("source/request/observation/trace lineage mismatch")
    # S27 ALREADY admitted the historical S29 observation at its original
    # inspected_at_ns. S24 then moved the ActionSupervisor's epoch clock
    # forward: re-invoking S27 as if this were a NEW current observation would
    # correctly fail. Recheck only immutable historical geometry/provenance,
    # without rolling back the owner clock or fabricating new source authority.
    coverage = obs.snapshot.nearby_entities_coverage
    matches = tuple(
        x for x in obs.snapshot.nearby_entities if x.entity_id == s.target_entity_id
    )
    if (
        s.target_name != "zombie"
        or type(s.target_entity_id) is not int
        or s.target_entity_id < 0
        or len(matches) != 1
        or matches[0].name != s.target_name
        or coverage.source_scope != MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE
        or coverage.max_distance != MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE
        or coverage.truncated
        or coverage.candidate_count != len(obs.snapshot.nearby_entities)
        or type(s.observed_at_ns) is not int
        or type(s.inspected_at_ns) is not int
        or type(s.max_age_ns) is not int
        or s.max_age_ns <= 0
        or s.observed_at_ns <= action3.events[-1].at_ns
        or not s.observed_at_ns <= s.inspected_at_ns <= s.observed_at_ns + s.max_age_ns
        or evidence.observed_at_ns != s.observed_at_ns
        or evidence.provenance != obs.provenance
        or evidence.evidence_id != (
            f"mineflayer:{obs.session_id}:{obs.seq}:entity-{s.target_entity_id}"
        )
    ):
        raise I1OwnerSeamRejected("historic S27 source scope/evidence invalid")
    pose = obs.snapshot.position
    target = matches[0]
    distance = math.dist(
        (pose.x, pose.y, pose.z),
        (target.position.x, target.position.y, target.position.z),
    )
    if (
        not math.isfinite(distance)
        or distance > coverage.max_distance
        or not math.isclose(distance, target.distance, rel_tol=0, abs_tol=1e-6)
        or not math.isclose(distance, s.calculated_distance_m, rel_tol=0, abs_tol=1e-6)
        or evidence.threat_clearance_cm != math.floor(distance * 100 + 0.5)
    ):
        raise I1OwnerSeamRejected("forged historical S27 geometry or distance")

    retention = read_retained_preference(
        current_retained, supplied_retained,
        required_target_id="risk_weight", expected_revision=1, provenance=provenance,
    )
    if (
        retention.snapshot.value != 4
        or trace.retained_revision != retention.revision
        or trace.world_evidence.provenance not in trace.source_provenance
    ):
        raise I1OwnerSeamRejected("S19 retained/current S24 evidence mismatch")

    cm = evidence.threat_clearance_cm
    if cm not in (20, 180):
        raise I1OwnerSeamRejected("World distance outside frozen I1 comparator")
    band = "near" if cm <= 100 else "far"
    wait_score = 2 * retention.snapshot.value if band == "near" else retention.snapshot.value
    reference = "WAIT" if wait_score < 7 else "MOVE_AWAY"
    if (
        trace.selected_candidate != reference
        or trace.wait_score != wait_score
        or trace.move_score != 7
        or trace.admission_status is not AdmissionDecisionStatus.ADMITTED
        or trace.stage_ids != STAGE_IDS
        or trace.epoch.cognition_requested
        or trace.epoch.timed_out_actions
    ):
        raise I1OwnerSeamRejected("S24 cheap fixed-score reference not qualified")

    if not isinstance(cognition, PersistentCognition):
        raise I1OwnerSeamRejected("actual mainline PersistentCognition owner required")
    if type(memory_id) is not str or not memory_id:
        raise I1OwnerSeamRejected("memory pointer ID must be nonempty")
    # Content is deliberately NOT inspected. Pointer alone is NOT the observation:
    # S29/S27 already provided the separate typed source evidence.
    matching = [m for m in cognition.memories if m.memory_id == memory_id]
    source_aliases = [
        m for m in cognition.memories if m.source_provenance == obs.provenance
    ]
    if (
        len(matching) != 1
        or len(source_aliases) != 1
        or matching[0] is not source_aliases[0]
        or matching[0].integration_provenance == obs.provenance
    ):
        raise I1OwnerSeamRejected("missing, duplicate or unqualified mainline Memory pointer")

    if not isinstance(repertoire, HabitRepertoire):
        raise I1OwnerSeamRejected("requires existing S11 HabitRepertoire")
    cue = HabitCue(
        cue_id=f"i1-{r.request_id}-{band}",
        features=(CueFeature("clearance_band", band),),
        provenance=obs.provenance,
    )
    choice = select_habit(repertoire, cue)
    candidate = choice.selected_candidate_ref
    if candidate is not None and candidate not in ("MOVE_AWAY", "WAIT"):
        raise I1OwnerSeamRejected("S11 candidate outside known S24 choice-space")
    agrees = choice.status is HabitSelectionStatus.SELECTED and candidate == reference
    return I1ReadOnlyResult(
        source_request_id=r.request_id,
        source_session=obs.session_id,
        source_seq=obs.seq,
        evidence_id=evidence.evidence_id,
        retained_revision=retention.revision,
        memory_id=matching[0].memory_id,
        habit_status=choice.status.value,
        habit_candidate=candidate,
        reference_candidate=reference,
        allocation_decision=(
            "CHEAP_MATCHES_REFERENCE" if agrees else "ESCALATE_CANDIDATE"
        ),
        requires_l2_candidate=not agrees,
    )
