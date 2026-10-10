"""Lane A E3: explicit epistemic S29 correlated probe -> S24 cognition.

This is an experiment-local caller boundary. No new controller, semantic owner,
Action issuance, autonomous scheduler, actual Minecraft source, or model use.
The World transport is caller-supplied; offline tests use an adapter double.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from adapters.mineflayer.execution import WorldConsequence
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.correlated_probe import (
    CorrelatedProbeGrant,
    CorrelatedProbeReceipt,
    CorrelatedProbeSession,
    request_correlated_post_action_probe,
)
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.postfailure_cognition import (
    PostFailureEpochTrace,
    run_explicit_postfailure_epoch,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

VERSION = "AC-A-E3-S29-S24-EPISTEMIC-SEAM-v1"
MANIFEST_SHA256 = "488cf7b7e7c317c697832d7e616bbba411df3018255fd3fd66c23d8f4462a769"
MANIFEST = {
    "version": VERSION,
    "source_base": "5424669a09a69eb364da559e38b9999fee7b6680",
    "parent_e2_head": "78be9d74950fd6b341bea40865b11f3bfdbfb320",
    "source_policy": "S24 fixed rev1 risk4 near<=100cm WAIT8 far>100cm WAIT4 MOVE_AWAY7",
    "source_mechanisms": [
        "S29 CorrelatedProbeGrant/ExclusiveProbeCursor/request_correlated_post_action_probe",
        "S27 SourceNativeThreatReceipt",
        "S24 run_explicit_postfailure_epoch",
    ],
    "prior": "explicit independent pre-declared near/far 1/2 each; not World observation",
    "observation_price_quarters": [1, 4],
    "initial_choices": ["WAIT", "OBSERVE"],
    "terminal_choices": ["WAIT", "MOVE_AWAY"],
    "metric": "frozen S24 comparison score plus stipulated observe cost; not physical utility",
    "paired_distances_cm": [20, 180],
    "alternative_arms": ["NO_OBSERVE", "CHEAP_EXACT", "OBSERVE"],
    "no_new_action": True,
    "model_calls": 0,
    "physical_minecraft_actions": 0,
    "claim_ceiling": "S29 adapter-double correlated receipt -> existing S24 eight-stage "
                     "readmission; no next issued Action or physical live-world outcome",
}


class EpistemicE3Rejected(ValueError):
    """Unqualified option or malformed source/owner gate."""


@dataclass(frozen=True, slots=True)
class EpistemicPlan:
    first: str
    price_quarters: int
    no_observe_expected_score: Fraction
    observe_expected_score: Fraction
    net_information_value: Fraction


@dataclass(frozen=True, slots=True)
class EpistemicResult:
    arm: str
    first: str
    selected: str
    observation_count: int
    next_epoch_count: int
    source_evidence_id: str | None
    correlated_request_id: str | None
    selected_score_with_cost: Fraction | None
    net_information_value: Fraction
    stage_ids: tuple[str, ...]
    receipt: CorrelatedProbeReceipt | None
    epoch: PostFailureEpochTrace | None
    model_calls: int = 0
    issued_actions: int = 0


def digest(manifest: object = MANIFEST) -> str:
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _require_frozen() -> None:
    if digest() != MANIFEST_SHA256:
        raise EpistemicE3Rejected("frozen E3 manifest drift")


def plan_epistemic(price_quarters: int) -> EpistemicPlan:
    """Only predeclared 50/50 future near/far uncertainty; never hidden World truth."""
    _require_frozen()
    if type(price_quarters) is not int or price_quarters not in (1, 4):
        raise EpistemicE3Rejected("price not prespecified (quarters)")
    # Frozen S24 rev1 near/far: WAIT 8/4, MOVE 7/7.
    no_obs = Fraction(8 + 4, 2)
    observed = Fraction(min(8, 7) + min(4, 7), 2) + Fraction(price_quarters, 4)
    value = no_obs - observed
    return EpistemicPlan(
        first="OBSERVE" if value > 0 else "WAIT",
        price_quarters=price_quarters,
        no_observe_expected_score=no_obs,
        observe_expected_score=observed,
        net_information_value=value,
    )


def _first_for_arm(arm: str, plan: EpistemicPlan) -> str:
    if arm == "NO_OBSERVE":
        return "WAIT"
    if arm == "OBSERVE":
        return "OBSERVE"  # explicit intervention, may be strictly suboptimal
    if arm == "CHEAP_EXACT":
        return plan.first
    raise EpistemicE3Rejected("unknown comparator arm")


async def continue_with_existing_owners(
    *,
    arm: str,
    price_quarters: int,
    adapter: CorrelatedProbeSession,
    cursor: ExclusiveProbeCursor,
    grant: CorrelatedProbeGrant,
    supervisor: ActionSupervisor,
    action: ActionLifecycle,
    consequence: WorldConsequence,
    recovery_skill: SkillExecution,
    intent: IntentCommitment,
    retained: LearningPreferenceState,
    observed_at_ns: int,
    inspected_at_ns: int,
    at_ns: int,
    provenance: Provenance,
    max_age_ns: int = 5,
    timeout_s: float = 0.05,
    max_frames: int = 4,
) -> EpistemicResult:
    """At most one S29 correlated observation then one actual S24 decision epoch.

    Critical: OBSERVE is an explicit caller-approved *read*, not an Action.
    E0 plan sees the stipulated prior only; no S29 response is read until chosen.
    The S24 pipeline returns ADMITTED candidate; no terminal next Action is issued.
    """
    p = plan_epistemic(price_quarters)
    first = _first_for_arm(arm, p)
    if not isinstance(supervisor, ActionSupervisor):
        raise EpistemicE3Rejected("exact supervised Action owner required")
    if supervisor.open_actions:
        raise EpistemicE3Rejected("another in-flight Action prevents epistemic step")
    if not isinstance(action, ActionLifecycle) or action.state is not ActionState.OUTCOME:
        raise EpistemicE3Rejected("requires past terminal Action OUTCOME")
    if supervisor.get(action.action_id) is not action:
        raise EpistemicE3Rejected("stale parent Action")
    if first == "WAIT":
        # A candidate score is NOT an observed World outcome or a new S24 epoch.
        return EpistemicResult(
            arm, first, "WAIT", 0, 0, None, None, None,
            p.net_information_value, (), None, None,
        )
    receipt = await request_correlated_post_action_probe(
        adapter, cursor, grant, supervisor, action, consequence,
        observed_at_ns=observed_at_ns, inspected_at_ns=inspected_at_ns,
        max_age_ns=max_age_ns, timeout_s=timeout_s, max_frames=max_frames,
    )
    evidence = receipt.source_receipt.evidence
    if (
        receipt.request_id != grant.request_id
        or receipt.acknowledged_request_id != grant.request_id
        or receipt.source_receipt.source.session_id != consequence.session_id
        or evidence.provenance != receipt.source_receipt.source.provenance
        or evidence.provenance == consequence.provenance
        or not evidence.evidence_id
    ):
        raise EpistemicE3Rejected("fresh source-bound E1 receipt missing")
    trace = run_explicit_postfailure_epoch(
        supervisor, action, consequence, recovery_skill, intent, retained,
        evidence, at_ns=at_ns, provenance=provenance,
    )
    if (
        evidence.provenance not in trace.source_provenance
        or trace.world_evidence is not evidence
        or len(trace.stage_ids) != 8
        or trace.selected_candidate not in ("WAIT", "MOVE_AWAY")
        or supervisor.open_actions
    ):
        raise EpistemicE3Rejected("source / S24 epoch / Action isolation violation")
    score = (
        trace.wait_score if trace.selected_candidate == "WAIT" else trace.move_score
    )
    return EpistemicResult(
        arm, first, trace.selected_candidate, 1, 1,
        evidence.evidence_id, receipt.request_id, Fraction(score) + Fraction(
            price_quarters, 4
        ), p.net_information_value, trace.stage_ids, receipt, trace,
    )
