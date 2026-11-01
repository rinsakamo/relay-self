"""Bounded L2 OPEN shadow on previous, *live* original S49/S16/S50 experience.

No model response changes World, S49's single Action issuer, L0, Goal, Memory or
learning. In a physical World the provider MUST be the already existing
RelayEngine→llama.cpp OPEN path; offline tests may explicitly use fixtures.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.l_mp11_g3_archived_l2_prefix import (
    MODEL_FAMILIES,
    NEXT_TESTS,
    RECONSIDERATIONS,
)
from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from adapters.mineflayer.l_mp11_typed_feedback import (
    RELATIONS,
    NumericRoleRejected,
    previous_feedback,
    validate_numeric_citations,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    OpenCognitionResult,
    RelayEngine,
)

PROPOSAL_FIELDS = frozenset({
    "referenced_prior_ordinals",
    "reconsideration",
    "model_family",
    "next_test",
    "explanation",
    "falsification_test",
    "predicted_wait_total_m",
    "capability_assessment",
    "prior_hypothesis_relation",
    "numeric_evidence_refs",
})
ABILITY = frozenset({"UNKNOWN", "CONDITIONAL_HYPOTHESIS"})
MAX_OPEN_BYTES = 2300
MAX_CALLS = 2
MAX_OPEN_DEADLINE_S = 50.0
SOURCE_CLASS = "LIVE_L2_PREVIOUS_EXPERIENCE_HYPOTHESIS_UNEXECUTED"


class JournaledLiveLlamaProvider(LlamaCppRelayProvider):
    """Canonical HTTP provider with L-only bounded output and original journal."""

    def __init__(self, *, journal_root: Path, **kwargs):
        super().__init__(**kwargs)
        self.calls: list[dict] = []
        self.journal_root = journal_root

    def _call(self, request_body, *, endpoint=None):
        request_body.update(max_tokens=512, response_format={"type": "json_object"})
        body = request_body
        entry = {"request": body, "endpoint": self.endpoint,
                 "started_monotonic_ns": time.monotonic_ns()}
        self.calls.append(entry)
        try:
            response = super()._call(body, endpoint=endpoint)
            entry["response"] = response
            return response
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            entry["finished_monotonic_ns"] = time.monotonic_ns()
            with (self.journal_root / f"llama-http-{len(self.calls)}.json").open("x") as out:
                json.dump(entry, out, ensure_ascii=False, indent=2, allow_nan=False)


class LiveL2Rejected(ValueError):
    """Fail closed on L2 provenance, source chronology, schema or call budget."""


@dataclass(frozen=True, slots=True)
class LiveL2Proposal:
    source_world_uuid: str
    source_subject_uuid: str
    source_session_id: str
    source_last_action_id: str
    source_last_prefix_sha256: str
    source_prior_count: int
    request_id: str
    referenced_prior_ordinals: tuple[int, ...]
    reconsideration: str
    model_family: str
    next_test: str
    explanation: str
    falsification_test: str
    predicted_wait_total_m: float | None
    capability_assessment: str
    prior_hypothesis_relation: str
    prior_proposal_sha256: str | None
    numeric_evidence_refs: tuple[dict, ...]
    proposal_sha256: str
    provider_source: str
    provider_prompt_tokens: int | None
    provider_completion_tokens: int | None
    provider_elapsed_ns: int
    classification: str = SOURCE_CLASS
    next_test_owner_approved: bool = False
    action_authority: bool = False
    model_structure_admitted: bool = False
    learning_admissions: int = 0
    l0_promotions: int = 0


def request_for_live_l2(
    ledger: LivePriorLedger, *, previous_proposal: LiveL2Proposal | None = None,
) -> OpenCognitionRequest:
    """Create a finite-shape hypothesis prompt with no later Action evidence."""
    if type(ledger) is not LivePriorLedger or not 1 <= len(ledger.history) <= 2:
        raise LiveL2Rejected("one or two previous completed original trials required")
    if len(ledger.history) == 1 and previous_proposal is not None:
        raise LiveL2Rejected("future L2 model cannot be visible on first trial")
    if len(ledger.history) == 2 and (
        type(previous_proposal) is not LiveL2Proposal
        or previous_proposal.source_world_uuid != ledger.world_uuid
        or previous_proposal.source_subject_uuid != ledger.subject_uuid
        or previous_proposal.source_session_id != ledger.session_id
        or previous_proposal.source_last_action_id != ledger.history[0].action_id
        or previous_proposal.source_last_prefix_sha256 != ledger.history[0].paper_prefix_sha256
    ):
        raise LiveL2Rejected("second proposal requires exact prior frozen L2 hypothesis")
    previous = ledger.model_request()
    feedback = None
    if previous_proposal is not None:
        try:
            feedback = previous_feedback(previous_proposal, ledger.history[-1])
        except NumericRoleRejected as exc:
            raise LiveL2Rejected("invalid prior L2 feedback") from exc
    previous = replace(
        previous,
        context=previous.context + (
            CognitionDatum.from_value(
                "previous_L2_hypothesis_typed_feedback",
                feedback if feedback is not None else {
                    "status": "FIRST_HYPOTHESIS_NOT_YET_TESTED",
                    "previous_proposal_sha256": None,
                    "model_revised_and_admitted": False,
                },
                Provenance(
                    "l.mp11.live.previous.hypothesis.feedback.readonly",
                    ledger.history[-1].paper_prefix_sha256,
                ),
            ),
        ),
    )
    schema = (
        "Respond in ONE JSON object with EXACT keys: "
        "referenced_prior_ordinals (sorted unique integer array of only "
        "previous completed trial numbers), reconsideration "
        "(KEEP_UNRESOLVED / QUESTION_APPLICABILITY / PROPOSE_STRUCTURAL_REVISION "
        "/ ABSTAIN), model_family (SINGLE_DECAY / PHASE_DEPENDENT / "
        "SURFACE_DEPENDENT / INITIAL_SPEED_DEPENDENT / OTHER_BOUNDED), next_test "
        "(CHECK_INITIAL_VELOCITY / CHECK_PAPER_CALLBACK_PHASE / "
        "VARY_INPUT_DURATION / COMPARE_GRASS_AND_ICE), "
        "explanation (16..200 characters), "
        "falsification_test (16..200 characters), predicted_wait_total_m "
        "(0..3 finite number or null), capability_assessment (UNKNOWN or "
        "CONDITIONAL_HYPOTHESIS). Cite only prior trial ordinals actually "
        "available, distinguish evidence from conjecture, and propose "
        "an UNAPPROVED next experiment. No Minecraft command, no "
        "performance superiority claim, no physical capability limit claim. "
        "Do not state that the proposal has been executed or learned."
        " Explain the numeric observed prediction error and cheap-zero comparison "
        "from the completed trials; distinguish these measurements from generic "
        "prior knowledge. Prior L2 feedback targets the FOLLOWING trial's "
        "WAIT8 TOTAL (m), NOT seven pair MAE (m). "
        "Return prior_hypothesis_relation: FIRST_HYPOTHESIS on first call; "
        "KEEP_PRIOR/REVISE_PRIOR/REJECT_PRIOR/ABSTAIN_ON_PRIOR on second. "
        "Return numeric_evidence_refs as 1..4 exact objects: metric_role, "
        "trial_ordinal, pair_index, value_m. Allowed role and pair index: "
        "WAIT8_TOTAL_M(0); PAPER_NEXT_TICK_PREDICTION_M(1..7); "
        "PAPER_NEXT_TICK_ABS_ERROR_M(1..7); "
        "PAPER_CHEAP_NEXT_TICK_MAE_M(0); "
        "PRIOR_L2_NEXT_WAIT8_PREDICTION_M(0, second call only); "
        "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M(0, second call only). "
        "Values must match the prior typed source, and these roles CANNOT "
        "be compared across targets. Do not call MAE a threshold or "
        "confuse predicted displacement and absolute error. "
        "For REVISE_PRIOR, cite at least one new trial measurement. "
        "Keep explanations brief enough for 512 output tokens."
    )
    return replace(previous, instruction=previous.instruction + "\n" + schema)


def parse_live_l2(
    ledger: LivePriorLedger,
    request: OpenCognitionRequest,
    result: OpenCognitionResult,
    *, require_real_llama: bool,
    previous_proposal: LiveL2Proposal | None = None,
) -> LiveL2Proposal:
    """Parse strict observed OPEN response, not a World command."""
    expected = request_for_live_l2(ledger, previous_proposal=previous_proposal)
    if (
        type(result) is not OpenCognitionResult
        or type(request) is not OpenCognitionRequest
        or request != expected
        or result.request_id != request.request_id
        or not result.provenance.source.strip()
        or (require_real_llama and result.provenance.source != "llama.cpp")
        or len(result.text.encode("utf-8")) > MAX_OPEN_BYTES
    ):
        raise LiveL2Rejected("missing genuine exact scoped live L2 response")
    try:
        raw = json.loads(result.text)
    except (ValueError, TypeError) as exc:
        raise LiveL2Rejected("OPEN response is not JSON") from exc
    if type(raw) is not dict or set(raw) != PROPOSAL_FIELDS:
        raise LiveL2Rejected("extra executable instructions or missing fields")
    refs = raw["referenced_prior_ordinals"]
    n = len(ledger.history)
    if (
        type(refs) is not list or len(refs) > n
        or any(type(x) is not int or x < 1 or x > n for x in refs)
        or len(set(refs)) != len(refs) or refs != sorted(refs)
        or type(raw["reconsideration"]) is not str
        or raw["reconsideration"] not in RECONSIDERATIONS
        or type(raw["model_family"]) is not str
        or raw["model_family"] not in MODEL_FAMILIES
        or type(raw["next_test"]) is not str
        or raw["next_test"] not in NEXT_TESTS
        or type(raw["capability_assessment"]) is not str
        or raw["capability_assessment"] not in ABILITY
        or type(raw["prior_hypothesis_relation"]) is not str
        or raw["prior_hypothesis_relation"] not in RELATIONS
        or any(type(raw[k]) is not str
               or not 16 <= len(raw[k]) <= 200 for k in (
                   "explanation", "falsification_test",
               ))
    ):
        raise LiveL2Rejected("unsupported, ungrounded or unbounded model hypothesis")
    prediction = raw["predicted_wait_total_m"]
    if prediction is not None and (
        type(prediction) not in (int, float)
        or not math.isfinite(prediction) or not 0 <= prediction <= 3
    ):
        raise LiveL2Rejected("invalid bounded next-WAIT prediction")
    if (
        raw["reconsideration"] in (
            "QUESTION_APPLICABILITY", "PROPOSE_STRUCTURAL_REVISION",
        ) and not refs
    ):
        raise LiveL2Rejected("model revision without referenced prior observation")
    relation = raw["prior_hypothesis_relation"]
    if (n == 1 and relation != "FIRST_HYPOTHESIS") or (
        n == 2 and relation == "FIRST_HYPOTHESIS"
    ):
        raise LiveL2Rejected("incorrect previous hypothesis relation")
    try:
        feedback = (
            previous_feedback(previous_proposal, ledger.history[-1])
            if previous_proposal is not None else None
        )
        citations = validate_numeric_citations(
            tuple(ledger.history), raw["numeric_evidence_refs"], feedback=feedback,
        )
    except NumericRoleRejected as exc:
        raise LiveL2Rejected("model numeric evidence is ungrounded") from exc
    if relation == "REVISE_PRIOR" and (
        feedback is None or feedback["previous_prediction_m"] is None
        or not any(c.trial_ordinal == 2 for c in citations)
    ):
        raise LiveL2Rejected("revision candidate lacks new-epoch observed evidence")
    source = ledger.history[-1]
    details = {
        "source_world_uuid": ledger.world_uuid,
        "source_subject_uuid": ledger.subject_uuid,
        "source_session_id": ledger.session_id,
        "source_last_action_id": source.action_id,
        "source_last_prefix_sha256": source.paper_prefix_sha256,
        "source_prior_count": n,
        "request_id": request.request_id,
        "referenced_prior_ordinals": tuple(refs),
        "reconsideration": raw["reconsideration"],
        "model_family": raw["model_family"],
        "next_test": raw["next_test"],
        "explanation": raw["explanation"],
        "falsification_test": raw["falsification_test"],
        "predicted_wait_total_m": (
            float(prediction) if prediction is not None else None
        ),
        "capability_assessment": raw["capability_assessment"],
        "prior_hypothesis_relation": relation,
        "prior_proposal_sha256": (
            previous_proposal.proposal_sha256 if previous_proposal is not None else None
        ),
        "numeric_evidence_refs": tuple(asdict(c) for c in citations),
        "provider_source": result.provenance.source,
        "provider_prompt_tokens": result.observed_prompt_tokens,
        "provider_completion_tokens": result.observed_completion_tokens,
        "provider_elapsed_ns": result.elapsed_ns,
    }
    digest = hashlib.sha256(json.dumps(
        details, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    return LiveL2Proposal(**details, proposal_sha256=digest)


class BoundedLiveL2:
    """One budget, no fallback, no replay, no Action rights."""

    def __init__(
        self,
        engine: RelayEngine, *, require_real_llama: bool = True,
        timeout_s: float = 45.0,
    ):
        if type(engine) is not RelayEngine or type(require_real_llama) is not bool:
            raise LiveL2Rejected("one existing RelayEngine and explicit source mode required")
        if (
            type(timeout_s) not in (float, int)
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_OPEN_DEADLINE_S
        ):
            raise LiveL2Rejected("strict bounded wall time required")
        self.engine = engine
        self.require_real_llama = require_real_llama
        self.timeout_s = float(timeout_s)
        self.proposals: list[LiveL2Proposal] = []
        self.attempted_request_ids: set[str] = set()
        self.failed_closed = False
        self.attempts: list[dict] = []

    async def propose_after(self, ledger: LivePriorLedger) -> LiveL2Proposal:
        if (
            self.failed_closed or len(self.proposals) >= MAX_CALLS
            or type(ledger) is not LivePriorLedger
            or len(ledger.history) != len(self.proposals) + 1
        ):
            raise LiveL2Rejected("duplicate, over-budget or gap in previous experience")
        previous = self.proposals[-1] if self.proposals else None
        req = request_for_live_l2(ledger, previous_proposal=previous)
        if req.request_id in self.attempted_request_ids:
            raise LiveL2Rejected("OPEN request already attempted")
        self.attempted_request_ids.add(req.request_id)
        entry = {"request": asdict(req),
                 "started_monotonic_ns": time.monotonic_ns()}
        self.attempts.append(entry)
        try:
            observed = await asyncio.wait_for(
                asyncio.to_thread(self.engine.open, req),
                timeout=self.timeout_s,
            )
            entry["result"] = asdict(observed)
            proposed = parse_live_l2(
                ledger, req, observed, require_real_llama=self.require_real_llama,
                previous_proposal=previous,
            )
        except Exception as exc:
            # A timed-out HTTP thread might finish later, but its result is
            # never read, admitted, retried, or used to grant a future Action.
            self.failed_closed = True
            entry["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            entry["finished_monotonic_ns"] = time.monotonic_ns()
        self.proposals.append(proposed)
        return proposed

    def public_report(self) -> dict:
        return {
            "classification": (
                "LIVE_L2_OPEN_SHADOW_PROPOSALS_NOT_EXECUTED"
                if not self.failed_closed else "LIVE_L2_FAILED_CLOSED"
            ),
            "proposals": [asdict(x) for x in self.proposals],
            "attempts": len(self.attempted_request_ids),
            "attempt_originals": self.attempts,
            "validated_open_calls": len(self.proposals),
            "provider_label_is_not_model_weights_attestation": True,
            "experiments_selected_and_executed_by_l2": 0,
            "new_action_issuers": 0,
            "learning_admissions": 0,
            "l0_promotions": 0,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
