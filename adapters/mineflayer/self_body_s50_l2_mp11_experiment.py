"""MP11 Stage 0: bounded L2-designed experimental questions in ONE World.

No World I/O or Action permission. An OPEN RelayEngine model chooses a hypothesis,
test condition, and prospective falsifiable displacement prediction. The host
may only accept a protected original S49/S16/Paper receipt from an independent
owner; this module NEVER issues a Minecraft command or admits learning.

Stage 0 uses synthetic receipts: `WorldTrialReceipt` is NOT source authentication.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Callable

from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    OpenCognitionResult,
)

MAX_TRIALS = 4
EXPERIMENTS = {
    "GRASS_SHORT": ("GRASS_BLOCK", "SHORT"),
    "ICE_SHORT": ("PACKED_ICE", "SHORT"),
    "GRASS_LONG": ("GRASS_BLOCK", "LONG"),
    "ICE_LONG": ("PACKED_ICE", "LONG"),
}
MODEL_FAMILIES = frozenset((
    "SINGLE_DECAY", "PHASE_DEPENDENT", "SURFACE_DEPENDENT",
    "INITIAL_SPEED_DEPENDENT", "OTHER_BOUNDED",
))
PRIOR_SOURCE = "MP10_DEV_ORIGINAL_TYPED_NEXT_NATIVE_EPOCH_NO_EFFECTIVE_REPAIR"


class MP11Rejected(ValueError):
    """L2 answer, owner boundary, trial order or source evidence is invalid."""


@dataclass(frozen=True, slots=True)
class L2ExperimentProposal:
    world_uuid: str
    subject_uuid: str
    round: int
    experiment_id: str
    model_family: str
    explanation: str
    falsification_test: str
    predicted_wait_total_m: float
    provider_source: str
    proposal_sha256: str
    source_status: str = "L2_OPEN_PROVIDER_PROPOSAL_NOT_WORLD_TRUTH"
    executable_action: bool = False
    learning_admission: int = 0


@dataclass(frozen=True, slots=True)
class WorldTrialReceipt:
    """Owner-facing fixture shape; source bytes must be verified OUTSIDE Stage 0."""
    world_uuid: str
    subject_uuid: str
    session_id: str
    proposal_sha256: str
    experiment_id: str
    action_id: str
    action_outcome: str
    wait_ticks: tuple[int, ...]
    wait_motion_m: tuple[float, ...]
    paper_original_sha256: str
    native_original_sha256: str
    source_status: str = "UNVERIFIED_OWNER_SUPPLIED_FIXTURE"


@dataclass(frozen=True, slots=True)
class TrialEvaluation:
    round: int
    experiment_id: str
    model_family: str
    proposal_sha256: str
    actual_wait_total_m: float
    predicted_wait_total_m: float
    absolute_error_m: float
    original_trial_world_uuid: str
    paper_original_sha256: str
    source_status: str = "UNVERIFIED_OWNER_SUPPLIED_FIXTURE"
    hypothesis_supported: str = "NOT_ESTABLISHED_WITH_ONE_TRIAL"
    cheap_rule_comparison: str = "NOT_YET_INDEPENDENTLY_COMPARABLE"
    learning_admissions: int = 0


def _seal(payload: dict) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def _token(x: str) -> bool:
    return isinstance(x, str) and 0 < len(x) <= 128 and not any(c.isspace() for c in x)


class L2ExperimentLoop:
    """One session / same World, model-produced next experiment, immutable budget.

    Open model is not trusted to mutate the World or determine its own authority.
    The caller must run original S49 Action, attest Paper/S16 source, and only
    then supply a sealed receipt. This Stage 0 does NOT provide that auditor.
    """

    def __init__(self, world_uuid: str, subject_uuid: str, session_id: str):
        if not all(_token(x) for x in (world_uuid, subject_uuid, session_id)):
            raise MP11Rejected("exact original same-World identifiers required")
        self.world_uuid = world_uuid
        self.subject_uuid = subject_uuid
        self.session_id = session_id
        self.pending: L2ExperimentProposal | None = None
        self.proposals: list[L2ExperimentProposal] = []
        self.receipts: list[WorldTrialReceipt] = []
        self.evaluations: list[TrialEvaluation] = []
        self._closed = False

    def l2_request(self) -> OpenCognitionRequest:
        if self._closed or self.pending is not None or len(self.receipts) >= MAX_TRIALS:
            raise MP11Rejected("L2 cannot plan over pending, stopped or exhausted World")
        used = {r.experiment_id for r in self.receipts}
        options = {k: {"surface": v[0], "relative_input": v[1]}
                   for k, v in EXPERIMENTS.items() if k not in used}
        if not options:
            raise MP11Rejected("no additional safe experiment")
        return OpenCognitionRequest(
            request_id=f"mp11:{self.world_uuid}:round-{len(self.receipts)+1}",
            instruction=(
                "You are L2, a fallible world-model scientist. Use PREVIOUS physical "
                "feedback to choose a falsifiable hypothesis and NEXT experiment, "
                "not a raw Minecraft command. Return exactly ONE JSON object with "
                "keys experiment_id, model_family, explanation, falsification_test, "
                "predicted_wait_total_m. Choose a single experiment_id from options. "
                "Never claim a learned rule, permit an Action, or alter safety policy. "
                "If evidence is insufficient you may refuse; unresolved is safer."
            ),
            intent_id="investigate-body-motion-error",
            focus="L2_MODEL_STRUCTURE_AND_APPLICABILITY_RECONSIDERATION",
            context=(
                CognitionDatum.from_value(
                    "epistemic_limits",
                    {"prior": PRIOR_SOURCE, "training_admission": False,
                     "one_world_until_explicit_end": True,
                     "prior_source_full_paper_qualified": False,
                     "current_world_observation": "HOST_FIXTURE_STAGE0_ONLY"},
                    Provenance("mp11.host.contract", "epistemic-stage0"),
                ),
                CognitionDatum.from_value(
                    "approved_experiment_conditions",
                    options, Provenance("mp11.host.safety", "four-approved-conditions"),
                ),
                CognitionDatum.from_value(
                    "previous_trials_readonly",
                    [asdict(x) for x in self.evaluations],
                    Provenance("mp11.host.readonly-ledger", self.world_uuid),
                ),
            ),
        )

    def propose(self, open_model: Callable[[OpenCognitionRequest], OpenCognitionResult]) -> L2ExperimentProposal:
        request = self.l2_request()
        if not callable(open_model):
            raise MP11Rejected("explicit OPEN L2 provider required; no scripted fallback")
        answer = open_model(request)
        if not isinstance(answer, OpenCognitionResult) or answer.request_id != request.request_id:
            raise MP11Rejected("no exact corresponding original L2 OPEN result")
        if not isinstance(answer.provenance, Provenance):
            raise MP11Rejected("L2 provider missing provenance")
        if not answer.text or len(answer.text.encode()) > 2048:
            raise MP11Rejected("empty or unbounded L2 hypothesis")
        try:
            candidate = json.loads(answer.text)
        except (TypeError, ValueError) as exc:
            raise MP11Rejected("non-JSON L2 proposal") from exc
        keys = {"experiment_id", "model_family", "explanation",
                "falsification_test", "predicted_wait_total_m"}
        if not isinstance(candidate, dict) or set(candidate) != keys:
            raise MP11Rejected("L2 must follow exact bounded hypothesis schema")
        used = {r.experiment_id for r in self.receipts}
        experiment = candidate["experiment_id"]
        if experiment not in EXPERIMENTS or experiment in used:
            raise MP11Rejected("L2 requested unsupported or duplicated experiment")
        family = candidate["model_family"]
        if family not in MODEL_FAMILIES:
            raise MP11Rejected("unbounded L2 model family not accepted")
        for key in ("explanation", "falsification_test"):
            val = candidate[key]
            if not isinstance(val, str) or not 15 <= len(val) <= 360:
                raise MP11Rejected("hypothesis must give bounded explicit rationale")
        predicted = candidate["predicted_wait_total_m"]
        if (type(predicted) not in (float, int)
                or not math.isfinite(predicted) or not 0 <= predicted <= 3):
            raise MP11Rejected("no finite falsifiable prospective displacement")
        fields = {
            "world_uuid": self.world_uuid,
            "subject_uuid": self.subject_uuid,
            "round": len(self.receipts)+1,
            "experiment_id": experiment,
            "model_family": family,
            "explanation": candidate["explanation"],
            "falsification_test": candidate["falsification_test"],
            "predicted_wait_total_m": float(predicted),
            "provider_source": answer.provenance.source,
        }
        proposal = L2ExperimentProposal(**fields, proposal_sha256=_seal(fields))
        self.pending = proposal
        self.proposals.append(proposal)
        return proposal

    def record_owner_result(self, receipt: WorldTrialReceipt) -> TrialEvaluation:
        p = self.pending
        if self._closed or p is None or not isinstance(receipt, WorldTrialReceipt):
            raise MP11Rejected("no matching pending L2 proposal")
        if (
            receipt.world_uuid != self.world_uuid
            or receipt.subject_uuid != self.subject_uuid
            or receipt.session_id != self.session_id
            or receipt.proposal_sha256 != p.proposal_sha256
            or receipt.experiment_id != p.experiment_id
            or not _token(receipt.action_id)
            or receipt.action_outcome != "S16_OUTCOME"
            or len(receipt.wait_ticks) != 8
            or len(receipt.wait_motion_m) != 8
            or any(type(t) is not int or t < 1 for t in receipt.wait_ticks)
            or any(b != a+1 for a,b in zip(receipt.wait_ticks[:-1],receipt.wait_ticks[1:]))
            or any(type(v) is not float or not math.isfinite(v) or v < 0
                   for v in receipt.wait_motion_m)
            or not all(isinstance(v, str) and len(v) == 64
                       and all(c in "0123456789abcdef" for c in v)
                       for v in (receipt.paper_original_sha256, receipt.native_original_sha256))
            or any(old.action_id == receipt.action_id for old in self.receipts)
            or any(old.wait_ticks[-1] >= receipt.wait_ticks[0]
                   for old in self.receipts)
        ):
            raise MP11Rejected("foreign, stale, replayed, unsafe or incomplete owner fixture")
        total = sum(receipt.wait_motion_m)
        result = TrialEvaluation(
            round=p.round, experiment_id=p.experiment_id, model_family=p.model_family,
            proposal_sha256=p.proposal_sha256,
            actual_wait_total_m=total,
            predicted_wait_total_m=p.predicted_wait_total_m,
            absolute_error_m=abs(total-p.predicted_wait_total_m),
            original_trial_world_uuid=self.world_uuid,
            paper_original_sha256=receipt.paper_original_sha256,
        )
        self.receipts.append(receipt)
        self.evaluations.append(result)
        self.pending = None
        return result

    def stop(self) -> None:
        if self.pending is not None:
            raise MP11Rejected("cannot silently drop an outstanding proposed experiment")
        self._closed = True

    def summary(self) -> dict:
        return {
            "world_uuid": self.world_uuid,
            "rounds_completed": len(self.receipts),
            "same_world_ledger": all(r.world_uuid == self.world_uuid for r in self.receipts),
            "l2_generated_proposals": len(self.proposals),
            "provider_required": True,
            "source_status": "UNVERIFIED_OWNER_SUPPLIED_FIXTURES_OFFLINE",
            "actual_minecraft_actions_issued_here": 0,
            "real_world_multi_trial_verified": False,
            "one_world_original_s49_multiple_actions": "NOT_YET_IMPLEMENTED",
            "prior_hypothesis_model_admitted": False,
            "l0_policy_mutations": 0,
            "learning_admissions": 0,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
