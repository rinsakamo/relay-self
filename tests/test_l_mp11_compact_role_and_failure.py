"""Offline controls for compact indexed L2 roles and failed-source reporting."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from adapters.mineflayer.l_mp11_compact_role_table import (
    CompactRoleTableRejected,
    compact_role_table,
)
from adapters.mineflayer.l_mp11_failure_source_snapshot import (
    SCOPE,
    summarize_closed_partial,
)
from adapters.mineflayer.l_mp11_live_l2_shadow import (
    BoundedLiveL2,
    request_for_live_l2,
)
from adapters.mineflayer.l_mp11_typed_feedback import previous_feedback
from test_l_mp11_live_l2_shadow import fixture_engine, output
from test_l_mp11_live_previous_action import accept, new_ledger


def first():
    ledger = new_ledger()
    accept(ledger, 1)
    return ledger


def test_exact_role_table_prevents_1_vs_0_pair_number_confusion():
    ledger = first()
    table = compact_role_table(ledger, feedback=None)
    req = request_for_live_l2(ledger)
    visible = json.loads(req.context[3].value_json)
    assert visible == table
    assert len(visible["trials"]) == 1
    assert visible["unit"] == "m"
    trial = visible["trials"][0]
    assert trial["trial_ordinal"] == 1
    assert trial["pair_index_0"]["WAIT8_TOTAL_M"] == pytest.approx(.4)
    assert trial["pair_index_0"]["PAPER_CHEAP_NEXT_TICK_MAE_M"] == pytest.approx(.05)
    pairs = trial["pair_index_1_to_7"]
    assert [x["pair_index"] for x in pairs] == list(range(1, 8))
    assert all(x["PAPER_NEXT_TICK_PREDICTION_M"] == pytest.approx(.0325)
               for x in pairs)
    assert all(x["PAPER_NEXT_TICK_ABS_ERROR_M"] == pytest.approx(.0175)
               for x in pairs)
    assert "UNAPPROVED" in req.instruction
    assert "512" in req.instruction
    assert "s49-native-move-18" not in req.context[1].value_json


def test_second_compact_role_table_ties_only_previous_prediction_to_new_trial():
    ledger = first()
    gate = BoundedLiveL2(fixture_engine(), require_real_llama=False)
    prior = asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    feedback = previous_feedback(prior, ledger.history[1])
    req = request_for_live_l2(ledger, previous_proposal=prior)
    visible = json.loads(req.context[3].value_json)
    assert visible["trials"][1]["trial_ordinal"] == 2
    assert visible["prior_L2_target"] == {
        "trial_ordinal": 2,
        "pair_index": 0,
        "PRIOR_L2_NEXT_WAIT8_PREDICTION_M": prior.predicted_wait_total_m,
        "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M": pytest.approx(.24),
    }
    assert feedback["previous_proposal_sha256"] == prior.proposal_sha256
    assert len(visible["trials"]) == 2
    assert visible["causal_surface_comparison_proven"] is False
    with pytest.raises(CompactRoleTableRejected):
        compact_role_table(ledger, feedback=None)


def test_short_open_prompt_keeps_exact_schema_and_safety_but_no_model_call():
    ledger = first()
    req = request_for_live_l2(ledger)
    assert len(req.instruction) < 3000
    assert all(x in req.instruction for x in [
        "referenced_prior_ordinals", "numeric_evidence_refs",
        "PAPER_NEXT_TICK_PREDICTION_M", "PAPER_NEXT_TICK_ABS_ERROR_M",
        "FIRST_HYPOTHESIS", "KEEP_PRIOR", "REVISE_PRIOR",
        "No causal surface proof",
    ])
    assert len(json.loads(req.context[3].value_json)["trials"]) == 1


def test_failure_capture_keeps_real_S16_partial_and_eof_without_qualifying():
    raw = b"original Paper line\n> "
    report = {
        "status": "FAIL",
        "actual_native_actions": [{"action": "s49-native-move-32"}],
        "mp11_g2": {"typed_s16_actions": [
            {"action_id": "s49-native-move-32", "native_seq": 51},
        ]},
        "l_mp11_live_prefix": {"observations": [{"ordinal": 1}]},
        "l_mp11_live_l2": {"attempts": 1, "validated_open_calls": 0},
    }
    witness = summarize_closed_partial(report, raw, predeclared=True)
    assert witness["classification"] == SCOPE
    assert witness["world_report_status_at_capture"] == "FAIL"
    assert witness["native_closed_action_count"] == 1
    assert witness["typed_s16_count"] == 1
    assert witness["native_action_ids"] == ["s49-native-move-32"]
    assert witness["l2_attempt_count"] == 1
    assert witness["valid_l2_open_count"] == 0
    assert witness["paper_full_original_sha256"] == hashlib.sha256(raw).hexdigest()
    assert witness["paper_eof_shape_only"]["suffix_hex"] == "3e20"
    assert witness["world_qualified_by_this_report"] is False
    assert witness["mandatory_g3_and_live_prefix_qualified"] is False
    assert report["status"] == "FAIL"


def test_malformed_or_missing_failure_eof_never_becomes_qualified():
    report = {
        "status": "FAIL",
        "actual_native_actions": [{"action": "original"}],
        "mp11_g2": {"typed_s16_actions": [{"action_id": "original"}]},
    }
    for raw, predeclared in ((b"truncated", True), (b"hello\n> ", False), (None, True)):
        r = summarize_closed_partial(report, raw, predeclared=predeclared)
        assert r["world_qualified_by_this_report"] is False
        assert r["mandatory_g3_and_live_prefix_qualified"] is False
        assert r["paper_eof_shape_only"] is None
        assert (raw is None) == (not r["original_paper_available"])
    assert report["status"] == "FAIL"


def test_original_runner_records_closed_action_before_llm_acceptance():
    source = Path("adapters/mineflayer/s49_normal_session_real_ci.py").read_text()
    start = source.index("        async def on_action(")
    end = source.index("        async def stage_world(", start)
    callback = source[start:end]
    assert callback.index('report["actual_native_actions"].append(') < callback.index(
        "hypothesis = await live_l2.propose_after("
    )
    assert "l2_stage_release[count].set()" in callback
    assert source.index('"l_mp11_postshutdown_partial_evidence"') < source.index(
        'report.get("status") == "PASS"):', source.index("finally:", source.index(
            "async def qualify("
        ))
    )


@pytest.mark.parametrize("count", [3, 4])
def test_compact_citation_budget_does_not_allow_unbounded_claims(count):
    from adapters.mineflayer.l_mp11_live_l2_shadow import LiveL2Rejected
    ledger = first()
    citation = {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 1,
                "pair_index": 0, "value_m": ledger.history[0].paper_wait_total_m}
    def more(req, *, mode):
        from relay_self.provenance import Provenance
        from relay_self.relay_engine import ProviderExpression
        value = output(req)
        value["numeric_evidence_refs"] = [citation] * count
        return ProviderExpression(
            text=json.dumps(value),
            provenance=Provenance("fake.fixture", "same-role-repeated"),
        )
    from relay_self.relay_engine import RelayEngine
    gate = BoundedLiveL2(RelayEngine(more), require_real_llama=False)
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))
    assert gate.failed_closed
