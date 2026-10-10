"""Lane A E4: E3 correlated WAIT -> second S29 receipt -> S25/S26 Action4 proposal.

Only caller-owned, experiment-local composition of FROZEN production mechanisms.
No new semantic state owner, automatic observation, Action authorization, issue
or World execution. Independent Action4 authorization and S15/S16 remain outside
these functions and must be supplied by an explicitly authorized caller.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.correlated_probe import (
    CorrelatedProbeGrant,
    CorrelatedProbeReceipt,
    CorrelatedProbeSession,
    request_correlated_post_action_probe,
)
from relay_self.execution_binding import ExecutionBinding
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.explicit_wait import (
    ExplicitWaitGate,
    ExplicitWaitReevaluation,
    WaitGateAuthority,
    acknowledge_explicit_wait,
    reevaluate_explicit_wait,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from relay_self.wait_release_action import (
    WaitReleaseActionAuthority,
    WaitReleaseActionTrace,
    propose_explicit_wait_release_action,
)

from experiments.epistemic_e3_s29_integration import EpistemicResult

VERSION = "AC-A-E4-S29-S25-S26-ACTION-OUTCOME-v1"
MANIFEST_SHA256 = "2aba8fa2cb7760afc1c5159b9e766e549ecaa40fd3b9e095e61a7ebf34b2c767"
MANIFEST = {
    "action4": "independent authorization, ISSUE, same S15 deterministic adapter double; "
               "distinct from S23 original Action3",
    "arms": ["NO_OBSERVE", "CHEAP_EXACT", "OBSERVE"],
    "base_e3": "2609a92648ca594a9fac3d8c3c4b60a4bf991e8c",
    "files": [
        "experiments/epistemic_e4_action_closure.py",
        "tests/test_epistemic_e4_action_closure.py",
        ".github/workflows/epistemic-e4-s29.yml",
    ],
    "frozen_upstream_s29": "5424669a09a69eb364da559e38b9999fee7b6680",
    "interpretation": "typed causal ordering only, fixed policy cheap comparator suffices; "
                      "no full E0 actor or learned L1",
    "negative": "wrong request ID/session/seq/replay, denied S25/S26 authority, stale "
                "Action/Intent, unauthorized Action4, late/missing/unknown World result; "
                "no inferred physical success",
    "observation_price_quarters": [1, 4],
    "scenario": "explicit correlated far(180cm)->S24 WAIT->S25 ACK->second "
                "correlated near(20cm) or far(180cm)->S25 fresh recheck->S26 "
                "proposal-only release if MOVE_AWAY->separately authorized Action4 "
                "S15 deterministic WorldConsequence and S16 terminal OUTCOME",
    "second_read": "explicit caller grant, not autonomous epistemic utility decision",
    "version": VERSION,
    "world": "offline Mineflayer adapter double only, not live Minecraft; "
             "0 LLM/physical action",
}


class E4Rejected(ValueError):
    """This caller composition cannot be used as independent Action authority."""


@dataclass(frozen=True, slots=True)
class E4SecondRead:
    first: EpistemicResult
    wait_gate: ExplicitWaitGate
    second_receipt: CorrelatedProbeReceipt
    # No S24 recheck before separate caller grant.


@dataclass(frozen=True, slots=True)
class E4Reconsidered:
    source: E4SecondRead
    reevaluation: ExplicitWaitReevaluation
    proposal: WaitReleaseActionTrace | None

    @property
    def selection(self) -> str:
        return self.reevaluation.result.selected_candidate


def digest(manifest: object = MANIFEST) -> str:
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _freeze() -> None:
    if digest() != MANIFEST_SHA256:
        raise E4Rejected("prospective E4 contract drift")


async def explicitly_read_after_wait(
    *,
    first: EpistemicResult,
    supervisor: ActionSupervisor,
    action3: ActionLifecycle,
    consequence3: WorldConsequence,
    recovery_skill: SkillExecution,
    intent: IntentCommitment,
    retained: LearningPreferenceState,
    ack_authority: WaitGateAuthority,
    ack_at_ns: int,
    expires_at_ns: int,
    ack_provenance: Provenance,
    adapter: CorrelatedProbeSession,
    cursor: ExclusiveProbeCursor,
    grant: CorrelatedProbeGrant,
    observed_at_ns: int,
    inspected_at_ns: int,
    max_age_ns: int = 5,
    timeout_s: float = 0.05,
    max_frames: int = 4,
) -> E4SecondRead:
    """Two separately authorized S29 reads, fresh S25 WAIT ACK but no new Action.

    The FIRST read and S24 epoch must already have happened in E3. This only
    consumes a different, newer correlated response after exact first receipt.
    """
    _freeze()
    if (
        not isinstance(first, EpistemicResult)
        or first.first != "OBSERVE"
        or first.selected != "WAIT"
        or first.observation_count != 1
        or first.next_epoch_count != 1
        or first.receipt is None
        or first.epoch is None
        or first.epoch.selected_candidate != "WAIT"
        or first.source_evidence_id != first.epoch.world_evidence.evidence_id
        or first.correlated_request_id != first.receipt.request_id
        or first.receipt.source_receipt.evidence is not first.epoch.world_evidence
    ):
        raise E4Rejected("real first E3 correlated WAIT evidence required")
    if (
        not isinstance(action3, ActionLifecycle)
        or action3.state is not ActionState.OUTCOME
        or not isinstance(supervisor, ActionSupervisor)
        or supervisor.get(action3.action_id) is not action3
        or not isinstance(consequence3, WorldConsequence)
        or first.receipt.source_receipt.source.session_id != consequence3.session_id
    ):
        raise E4Rejected("first evidence/Action3 exact parent mismatch")
    if (
        not isinstance(cursor, ExclusiveProbeCursor)
        or cursor.consumed
        or cursor.session_id != consequence3.session_id
        or cursor.next_seq != first.receipt.next_cursor_seq
        or not isinstance(grant, CorrelatedProbeGrant)
        or grant.request_id == first.receipt.request_id
    ):
        raise E4Rejected("a different fresh correlated S29 request is required")
    gate = acknowledge_explicit_wait(
        first.epoch, supervisor, action3, consequence3, recovery_skill,
        intent, retained, ack_authority, at_ns=ack_at_ns,
        expires_at_ns=expires_at_ns, provenance=ack_provenance,
    )
    receipt = await request_correlated_post_action_probe(
        adapter, cursor, grant, supervisor, action3, consequence3,
        observed_at_ns=observed_at_ns, inspected_at_ns=inspected_at_ns,
        max_age_ns=max_age_ns, timeout_s=timeout_s, max_frames=max_frames,
        previous_receipt=first.receipt,
    )
    ev = receipt.source_receipt.evidence
    if (
        receipt.request_id != grant.request_id
        or receipt.acknowledged_request_id != grant.request_id
        or receipt.probe_seq <= first.receipt.probe_seq
        or ev.provenance == first.epoch.world_evidence.provenance
        or ev.evidence_id == first.epoch.world_evidence.evidence_id
        or ev.observed_at_ns <= gate.armed_at_ns
        or ev.observed_at_ns > gate.expires_at_ns
    ):
        raise E4Rejected("not distinct fresh same-lineage World evidence")
    return E4SecondRead(first, gate, receipt)


def explicitly_reconsider_and_propose(
    source: E4SecondRead,
    *,
    recheck_authority: WaitGateAuthority,
    recheck_at_ns: int,
    recheck_provenance: Provenance,
    release_authority: WaitReleaseActionAuthority | None = None,
    binding: ExecutionBinding | None = None,
    propose_at_ns: int = 95,
    proposal_provenance: Provenance | None = None,
) -> E4Reconsidered:
    """Separate caller S25 recheck. S26 proposal only if newly MOVE_AWAY."""
    _freeze()
    if not isinstance(source, E4SecondRead):
        raise E4Rejected("requires exact second correlated WAIT read")
    gate = source.wait_gate
    receipt = source.second_receipt
    if (
        not isinstance(receipt, CorrelatedProbeReceipt)
        or receipt.source_receipt.evidence.evidence_id
        == source.first.source_evidence_id
        or receipt.request_id == source.first.correlated_request_id
        or receipt.probe_seq <= source.first.receipt.probe_seq
    ):
        raise E4Rejected("replayed or mismatched second read")
    reevaluation = reevaluate_explicit_wait(
        gate, receipt.source_receipt.evidence, recheck_authority,
        at_ns=recheck_at_ns, provenance=recheck_provenance,
    )
    if reevaluation.result.selected_candidate == "WAIT":
        if release_authority is not None or binding is not None:
            raise E4Rejected("WAIT is a non-Action; no proposal grant may be consumed")
        return E4Reconsidered(source, reevaluation, None)
    if reevaluation.result.selected_candidate != "MOVE_AWAY":
        raise E4Rejected("unadmitted/unrecognized plan cannot become Action")
    if proposal_provenance is None:
        raise E4Rejected("explicit caller proposal provenance required")
    trace = propose_explicit_wait_release_action(
        reevaluation, recheck_authority, release_authority, binding,
        at_ns=propose_at_ns, provenance=proposal_provenance,
    )
    return E4Reconsidered(source, reevaluation, trace)
