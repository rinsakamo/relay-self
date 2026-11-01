"""Future Paper EOF and typed L2 numeric feedback: strictly offline fixtures."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace

import pytest

from adapters.mineflayer.l_mp11_paper_eof_envelope import (
    PaperEOFRejected,
    seal_after_shutdown,
    verified_complete_lines,
)
from adapters.mineflayer.l_mp11_typed_feedback import (
    NumericRoleRejected,
    numeric_value,
    previous_feedback,
    validate_numeric_citations,
)
from adapters.mineflayer.self_body_s50_l2_mp11_paper_audit import (
    MP11PaperRejected,
    audit_multi_trial_paper,
)
from test_l_mp11_live_l2_shadow import fixture_engine
from test_l_mp11_live_previous_action import accept, new_ledger
from test_self_body_s50_l2_mp11_paper_audit import (
    MARKERS,
    SUBJECT,
    WORLD,
    original,
)

def test_future_predeclared_eof_exact_prompt_keeps_unmodified_original_sha():
    lines = original()
    raw = lines + b"> "
    envelope = asdict(seal_after_shutdown(raw, predeclared=True))
    assert envelope["original_length"] == len(raw)
    assert envelope["complete_lines_length"] == len(lines)
    assert envelope["suffix_hex"] == "3e20"
    assert envelope["end_state"] == "JLINE_PROMPT_2_BYTES"
    assert envelope["original_sha256"] != envelope["complete_lines_sha256"]
    assert verified_complete_lines(raw, envelope, predeclared=True) == lines
    assert len(audit_multi_trial_paper(
        lines, action_markers=MARKERS, world_uuid=WORLD,
        subject_uuid=SUBJECT, surfaces=("GRASS_BLOCK", "PACKED_ICE"),
    )) == 2
    with pytest.raises(MP11PaperRejected):
        audit_multi_trial_paper(
            raw, action_markers=MARKERS, world_uuid=WORLD,
            subject_uuid=SUBJECT, surfaces=("GRASS_BLOCK", "PACKED_ICE"),
        )


@pytest.mark.parametrize("tail", [
    b">", b">  ", b"> \nTRUNCATED", b"PartialPaper", b"\x00",
    b"> \r", b"> \x1b[31m", b"S50_DEV_WAIT_TICK marker_id=foreign",
    b"> > ", b"\n> ",
])
def test_unknown_or_ambiguous_incomplete_shutdown_suffix_denied(tail):
    with pytest.raises(PaperEOFRejected):
        seal_after_shutdown(original() + tail, predeclared=True)


def test_missing_or_postfacto_opt_in_and_forged_envelope_denied():
    raw = original() + b"> "
    with pytest.raises(PaperEOFRejected):
        seal_after_shutdown(raw, predeclared=False)
    truth = asdict(seal_after_shutdown(raw, predeclared=True))
    for field, value in (
        ("original_length", len(raw) - 1),
        ("original_sha256", "a" * 64),
        ("suffix_hex", "00"),
        ("admission", "QUALIFIED_HISTORICAL_RUN"),
    ):
        corrupted = truth | {field: value}
        with pytest.raises(PaperEOFRejected):
            verified_complete_lines(raw, corrupted, predeclared=True)
    with pytest.raises(PaperEOFRejected):
        verified_complete_lines(raw, truth, predeclared=False)
    with pytest.raises(PaperEOFRejected):
        verified_complete_lines(raw + b"x", truth, predeclared=True)


def test_clean_eof_is_still_strict_and_retains_empty_suffix():
    raw = original()
    info = asdict(seal_after_shutdown(raw, predeclared=True))
    assert info["suffix_hex"] == ""
    assert info["end_state"] == "EXACT_COMPLETE_LINES"
    assert verified_complete_lines(raw, info, predeclared=True) == raw


def test_previous_hypothesis_is_matched_to_next_wait8_total_not_cheap_mae():
    from adapters.mineflayer.l_mp11_live_l2_shadow import BoundedLiveL2
    ledger = new_ledger()
    accept(ledger, 1)
    gate = BoundedLiveL2(fixture_engine(), require_real_llama=False)
    prev = asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    fb = previous_feedback(prev, ledger.history[-1])
    assert fb["previous_proposal_sha256"] == prev.proposal_sha256
    assert fb["target_kind"] == "NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M"
    assert fb["target_trial_ordinal"] == 2
    assert fb["previous_prediction_m"] == pytest.approx(.16)
    assert fb["target_observed_m"] == pytest.approx(.4)
    assert fb["prior_prediction_abs_error_m"] == pytest.approx(.24)
    assert "NOT_COMPARABLE" in fb["comparator_scope"]
    assert fb["model_revised_and_admitted"] is False
    assert numeric_value(
        tuple(ledger.history), "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M",
        2, 0, feedback=fb,
    ) == pytest.approx(.24)
    with pytest.raises(NumericRoleRejected):
        numeric_value(
            tuple(ledger.history), "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M",
            1, 0, feedback=fb,
        )


@pytest.mark.parametrize("citation", [
    {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 1,
     "pair_index": 1, "value_m": .4},
    {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 3,
     "pair_index": 0, "value_m": .4},
    {"metric_role": "PAPER_NEXT_TICK_ABS_ERROR_M", "trial_ordinal": 1,
     "pair_index": 1, "value_m": .0325},
    {"metric_role": "PAPER_NEXT_TICK_PREDICTION_M", "trial_ordinal": 1,
     "pair_index": 0, "value_m": .0325},
    {"metric_role": "PAPER_CHEAP_NEXT_TICK_MAE_M", "trial_ordinal": 1,
     "pair_index": 0, "value_m": .4},
    {"metric_role": "NEXT_TICK_ERROR_THRESHOLD", "trial_ordinal": 1,
     "pair_index": 0, "value_m": .4},
    {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": True,
     "pair_index": 0, "value_m": .4},
    {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 1,
     "pair_index": 0, "value_m": float("nan")},
    {"metric_role": "PRIOR_L2_NEXT_WAIT8_PREDICTION_M", "trial_ordinal": 1,
     "pair_index": 0, "value_m": .16},
])
def test_unavailable_future_wrong_pair_wrong_role_or_fake_value_rejected(citation):
    ledger = new_ledger()
    accept(ledger, 1)
    with pytest.raises(NumericRoleRejected):
        validate_numeric_citations(
            tuple(ledger.history), [citation], feedback=None,
        )


def test_exact_citations_and_duplicate_citation_denied():
    ledger = new_ledger()
    accept(ledger, 1)
    source = ledger.history[0]
    ref = {"metric_role": "PAPER_NEXT_TICK_ABS_ERROR_M",
           "trial_ordinal": 1, "pair_index": 1,
           "value_m": source.paper_next_abs_error_m[0]}
    assert validate_numeric_citations(
        tuple(ledger.history), [ref], feedback=None,
    )[0].value_m == pytest.approx(source.paper_next_abs_error_m[0])
    with pytest.raises(NumericRoleRejected):
        validate_numeric_citations(
            tuple(ledger.history), [ref, ref], feedback=None,
        )
