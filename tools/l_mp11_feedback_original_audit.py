"""Reconstruct prospective L feedback from original Paper prefixes and OPEN text.

No model call or physical Action. Shared strict parsers are independently run
against originals, rather than trusting the host's validated-call counter.
"""
from __future__ import annotations

from dataclasses import asdict

from adapters.mineflayer.l_mp11_live_l2_shadow import parse_live_l2, request_for_live_l2
from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from relay_self.provenance import Provenance
from relay_self.relay_engine import OpenCognitionResult, ProviderCallFacts


def audit_feedback_originals(report: dict, original: bytes) -> dict:
    g3 = report["mp11_g3"]
    ledger = LivePriorLedger(session_id=report["session_id"],
                             world_uuid=g3["paper_world_uuid"],
                             subject_uuid=g3["subject_uuid"])
    shadow = report["l_mp11_live_l2"]
    evidence_ids = shadow.get("evidence_id_mode", False)
    if type(evidence_ids) is not bool:
        raise ValueError("invalid original evidence mode")
    attempts = shadow["attempt_originals"]
    windows = report["l_mp11_live_prefix"]["observations"]
    if type(attempts) is not list or len(attempts) != 2:
        raise ValueError("two original OPEN attempts required")
    previous = None
    last_finish = 0
    for i, attempt in enumerate(attempts):
        window = windows[i]
        native = report["mp11_g2"]["typed_s16_actions"][i]
        ledger.accept_completed(
            original[:window["paper_prefix_length"]],
            action_id=native["action_id"],
            marker_id=g3["paper_markers"][i],
            native_s16_seq=native["native_seq"], native_outcome="S16_OUTCOME",
        )
        request = request_for_live_l2(
            ledger, previous_proposal=previous, evidence_ids=evidence_ids,
        )
        # JSON-normalize tuple fields without accepting altered source values.
        import json
        if json.loads(json.dumps(asdict(request))) != attempt["request"]:
            raise ValueError("original OPEN request differs from prior-only reconstruction")
        start, finish = attempt["started_monotonic_ns"], attempt["finished_monotonic_ns"]
        if (type(start) is not int or type(finish) is not int
                or not last_finish < start < finish or "error" in attempt):
            raise ValueError("OPEN chronology/error mismatch")
        raw = attempt["result"]
        result = OpenCognitionResult(
            request_id=raw["request_id"], text=raw["text"],
            provenance=Provenance(**raw["provenance"]),
            elapsed_ns=raw["elapsed_ns"],
            call_facts=ProviderCallFacts(**raw["call_facts"]),
        )
        proposal = parse_live_l2(ledger, request, result, require_real_llama=True,
                                 previous_proposal=previous,
                                 evidence_ids=evidence_ids)
        if json.loads(json.dumps(asdict(proposal))) != shadow["proposals"][i]:
            raise ValueError("original model text/proposal SHA/numeric citation mismatch")
        previous = proposal
        last_finish = finish
    return {"two_prior_only_requests_reconstructed": True,
            "h1_to_feedback_to_h2_sha_verified": True,
            "numeric_citations_reparsed": True,
            "evidence_ids_resolved_from_original": evidence_ids,
            "causal_interpretation_attested": False}
