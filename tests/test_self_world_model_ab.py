"""W4 SelfWorld local-model matched A/B: synthetic fake provider only."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from experiments.self_world_model_ab import (
    ARM_BASE,
    ARM_CONTEXT,
    W4ModelABBlocked,
    _synthetic_cases,
    _write_new_report,
    ab_requests,
    paired_order,
    run_matched_ab,
    validate_local_endpoint,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderCallFacts,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)


def _stub(request, *, mode):
    data = {item.key: json.loads(item.value_json) for item in request.context}
    seen = data.get("self_world_observed", [])
    review = data.get("self_world_prediction_review")
    choice = "INSPECT_SOURCE" if seen and (
        review is None or review["status"] == "match"
    ) else "DEFER_RECHECK"
    facts = ProviderCallFacts(
        prompt_tokens=40 + 20 * len(data),
        completion_tokens=4,
        total_tokens=44 + 20 * len(data),
    )
    if mode is CognitionMode.OPEN:
        return ProviderExpression("synthetic hypothesis", Provenance(
            "synthetic", "open",
        ), facts)
    if mode is CognitionMode.BOUNDED and review:
        return ProviderDecision(DecisionStatus.UNRESOLVED, None, "think", facts)
    return ProviderDecision(DecisionStatus.RESOLVED, choice, "synthetic", facts)


def test_only_context_differs_between_arms():
    cases = _synthetic_cases()
    assert [c.case_id for c in cases] == [
        "match", "mismatch", "unknown", "synthetic-empty",
    ]
    assert paired_order(0) == (ARM_BASE, ARM_CONTEXT)
    assert paired_order(1) == (ARM_CONTEXT, ARM_BASE)
    a, b = ab_requests(cases[0].prepared, "following", "bounded")
    assert not a.context and b.context
    assert replace(b, context=()) == a
    assert [d.key for d in b.context] == [
        "self_world_observer", "self_world_observed",
        "self_world_prediction_review",
    ]
    c, d = ab_requests(cases[0].prepared, "following", "open")
    assert replace(d, context=()) == c
    assert d.context == b.context
    assert a.instruction == b.instruction and a.choices == b.choices


def test_stubs_measure_order_latency_usage_and_bounded_think_open():
    result = run_matched_ab(
        cases=_synthetic_cases(), engine=RelayEngine(_stub),
        repeats=2, warmup_pairs=1,
    )
    assert result["classification"] == "DEV_ONLY_LOCAL_MODEL_OBSERVATION_NOT_SCIENCE"
    assert result["new_world_runs"] == result["physical_actions"] == 0
    assert result["s10_commits"] == result["outcomes"] == 0
    assert len(result["rows"]) == 4 * 2 * 2 * 3 * 2
    measured = [r for r in result["rows"] if not r["warmup"]]
    assert len(measured) == 4 * 2 * 2 * 2 * 2
    assert all(row["error_type"] is None for row in result["rows"])
    yes = result["summary"]["match/following/bounded/with_selfworld"]
    no = result["summary"]["match/following/bounded/without_selfworld"]
    assert yes["rubric_correct"] == 2 and no["rubric_correct"] == 0
    assert yes["think_escalations"] == 2 and no["think_escalations"] == 0
    assert yes["token_metadata_complete"] and no["token_metadata_complete"]
    assert yes["prompt_tokens_median"] > no["prompt_tokens_median"]
    assert all(r["open_text_sha256"] for r in measured if r["route"] == "open")
    assert all("raw_open_text" not in r for r in measured)


def test_synthetic_unknown_and_empty_never_claim_world_absence():
    case = next(c for c in _synthetic_cases() if c.case_id == "synthetic-empty")
    result = run_matched_ab(
        cases=(case,), engine=RelayEngine(_stub),
        repeats=1, warmup_pairs=0, include_open=False,
    )
    assert all(r["choice_id"] == "DEFER_RECHECK" for r in result["rows"])
    assert all(r["correct_rubric"] for r in result["rows"])


@pytest.mark.parametrize("bad", [
    "http://localhost:1234/v1/chat/completions",
    "http://example.org:1234/v1/chat/completions",
    "https://127.0.0.1:1234/v1/chat/completions",
    "http://127.0.0.1:1234/other",
    "http://127.0.0.1:1234/v1/chat/completions?x=1",
    "http://u:p@127.0.0.1:1234/v1/chat/completions",
    "http://127.0.0.1:bad/v1/chat/completions",
    "file:///v1/chat/completions",
])
def test_no_nonlocal_model_endpoint(bad):
    with pytest.raises(W4ModelABBlocked):
        validate_local_endpoint(bad)


def test_exclusive_report_and_exact_local_endpoint(tmp_path):
    from experiments.self_world_model_ab import _check_new_path

    uri = "http://127.0.0.1:1234/v1/chat/completions"
    assert validate_local_endpoint(uri) == uri
    target = tmp_path / "report.json"
    _check_new_path(target)
    _write_new_report(target, {"rows": [], "source": "dev"})
    assert json.loads(target.read_text()) == {"rows": [], "source": "dev"}
    with pytest.raises(W4ModelABBlocked):
        _check_new_path(target)
    with pytest.raises(W4ModelABBlocked):
        _write_new_report(target, {"rows": ["mutate"]})


@pytest.mark.parametrize("bad", [
    "duplicate", "wrong_expected", "fake_action", "fake_s10", "empty",
    "no_repeat", "no_context", "bad_epoch", "bad_run",
])
def test_fail_closed_on_fake_authority_or_invalid_protocol(bad):
    cases = _synthetic_cases()
    case = cases[0]
    params = dict(
        cases=(case,), engine=RelayEngine(_stub),
        repeats=1, warmup_pairs=0, include_open=False,
    )
    if bad == "no_context":
        with pytest.raises(W4ModelABBlocked):
            ab_requests(replace(
                case.prepared,
                following_bounded=replace(case.prepared.following_bounded, context=()),
            ), "following", "bounded")
        return
    if bad == "bad_epoch":
        with pytest.raises(W4ModelABBlocked):
            ab_requests(case.prepared, "absent", "bounded")
        return
    if bad == "duplicate":
        params["cases"] = (case, case)
    elif bad == "wrong_expected":
        params["cases"] = (replace(case, expected_prior="WORLD_SAFE"),)
    elif bad == "fake_action":
        params["cases"] = (replace(case, prepared=replace(
            case.prepared, action_count=1,
        )),)
    elif bad == "fake_s10":
        params["cases"] = (replace(case, prepared=replace(
            case.prepared, s10_update_count=1,
        )),)
    elif bad == "empty":
        params["cases"] = ()
    elif bad == "no_repeat":
        params["repeats"] = 0
    else:
        params["cases"] = (replace(case, source_class="WORLD_QUALIFIED"),)
    with pytest.raises(W4ModelABBlocked):
        run_matched_ab(**params)


def test_provider_failure_is_not_a_rubric_pass():
    from adapters.llama_cpp.relay_engine import LlamaCppProviderError

    def failed(_request, *, mode):
        raise LlamaCppProviderError("fixture offline failure")

    result = run_matched_ab(
        cases=(_synthetic_cases()[0],), engine=RelayEngine(failed),
        repeats=1, warmup_pairs=0, include_open=False,
    )
    assert all(r["error_type"] == "LlamaCppProviderError" for r in result["rows"])
    assert all(r["correct_rubric"] is None for r in result["rows"])
    assert all(g["errors"] == 1 for g in result["summary"].values())
    assert all(not g["token_metadata_complete"] for g in result["summary"].values())


def test_per_observation_journal_callback_sees_every_attempt():
    seen = []
    run = run_matched_ab(
        cases=(_synthetic_cases()[0],), engine=RelayEngine(_stub),
        repeats=2, warmup_pairs=1, include_open=False,
        on_record=lambda item: seen.append(item),
    )
    assert seen == run["rows"]
    assert len(seen) == 2 * 3 * 2
    assert len([item for item in seen if not item["warmup"]]) == 2 * 2 * 2
    assert seen[0]["arm"] == ARM_BASE
    assert seen[2]["arm"] == ARM_CONTEXT
