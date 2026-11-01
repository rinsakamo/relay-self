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
from dataclasses import asdict, dataclass, replace

from adapters.mineflayer.l_mp11_g3_archived_l2_prefix import (
    MODEL_FAMILIES,
    NEXT_TESTS,
    RECONSIDERATIONS,
)
from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from relay_self.relay_engine import (
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
})
ABILITY = frozenset({"UNKNOWN", "CONDITIONAL_HYPOTHESIS"})
MAX_OPEN_BYTES = 2300
MAX_CALLS = 2
MAX_OPEN_DEADLINE_S = 50.0
SOURCE_CLASS = "LIVE_L2_PREVIOUS_EXPERIENCE_HYPOTHESIS_UNEXECUTED"


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


def request_for_live_l2(ledger: LivePriorLedger) -> OpenCognitionRequest:
    """Create a finite-shape hypothesis prompt with no later Action evidence."""
    if type(ledger) is not LivePriorLedger or not 1 <= len(ledger.history) <= 2:
        raise LiveL2Rejected("one or two previous completed original trials required")
    previous = ledger.model_request()
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
    )
    return replace(previous, instruction=previous.instruction + "\n" + schema)


def parse_live_l2(
    ledger: LivePriorLedger,
    request: OpenCognitionRequest,
    result: OpenCognitionResult,
    *, require_real_llama: bool,
) -> LiveL2Proposal:
    """Parse strict observed OPEN response, not a World command."""
    expected = request_for_live_l2(ledger)
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

    async def propose_after(self, ledger: LivePriorLedger) -> LiveL2Proposal:
        if (
            self.failed_closed or len(self.proposals) >= MAX_CALLS
            or type(ledger) is not LivePriorLedger
            or len(ledger.history) != len(self.proposals) + 1
        ):
            raise LiveL2Rejected("duplicate, over-budget or gap in previous experience")
        req = request_for_live_l2(ledger)
        if req.request_id in self.attempted_request_ids:
            raise LiveL2Rejected("OPEN request already attempted")
        self.attempted_request_ids.add(req.request_id)
        try:
            observed = await asyncio.wait_for(
                asyncio.to_thread(self.engine.open, req),
                timeout=self.timeout_s,
            )
            proposed = parse_live_l2(
                ledger, req, observed, require_real_llama=self.require_real_llama,
            )
        except Exception:
            # A timed-out HTTP thread might finish later, but its result is
            # never read, admitted, retried, or used to grant a future Action.
            self.failed_closed = True
            raise
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
            "validated_open_calls": len(self.proposals),
            "provider_label_is_not_model_weights_attestation": True,
            "experiments_selected_and_executed_by_l2": 0,
            "new_action_issuers": 0,
            "learning_admissions": 0,
            "l0_promotions": 0,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
