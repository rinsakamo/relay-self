"""Archived G3 L2 context must never impersonate live inference or future evidence."""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.l_mp11_g3_archived_l2_prefix import (
    G3PrefixRejected,
    freeze_archived_prefix,
    make_l2_request,
    parse_g3_readback,
    shadow_l2_preview,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionResult,
    ProviderExpression,
    RelayEngine,
)

PATH = Path(
    "docs/evidence/issue653-mp11-g3-one-paper-world-20261101/"
    "run1/independent-native-paper-readback.json"
)


def original():
    return json.loads(PATH.read_text(encoding="utf-8"))


def fake_result(request):
    prior = json.loads(request.context[1].value_json)
    n = len(prior)
    assert request.focus == "L2_ARCHIVED_G3_CAUSAL_HYPOTHESIS_PREVIEW_ONLY"
    assert request.context[0].provenance.source == "mp11.g3.archived.report.readonly"
    choice = "KEEP_UNRESOLVED" if n == 0 else (
        "QUESTION_APPLICABILITY" if n == 1
        else "PROPOSE_STRUCTURAL_REVISION"
    )
    payload = {
        "referenced_prior_ordinals": list(range(1, n + 1)),
        "reconsideration": choice,
        "model_family": "PHASE_DEPENDENT",
        "next_test": "CHECK_PAPER_CALLBACK_PHASE",
        "explanation": "The archived observation does not distinguish initial speed from callback phase.",
        "falsification_test": "Freeze the prediction before future measurement and compare condition controls.",
        "predicted_wait_total_m": None,
    }
    return OpenCognitionResult(
        request_id=request.request_id,
        text=json.dumps(payload),
        provenance=Provenance("fake.fixture", "not-real-gemma"),
    )


@pytest.mark.parametrize("n", [0, 1, 2])
def test_archived_completed_prefix_only_no_future_exposure(n):
    data = original()
    prefix = freeze_archived_prefix(data, visible_count=n)
    trials = parse_g3_readback(data)
    assert prefix.previous_trials == trials[:n]
    assert prefix.source_status.endswith("NOT_LIVE_SOURCE")
    assert prefix.physically_online_at_prefix is False
    assert prefix.original_bytes_reauthenticated is False
    req = make_l2_request(prefix)
    history = json.loads(req.context[1].value_json)
    assert [item["action_id"] for item in history] == [
        x.action_id for x in trials[:n]
    ]
    for t in trials[n:]:
        assert t.action_id not in req.context[1].value_json
    limits = json.loads(req.context[0].value_json)
    assert limits["actual_gemma_calls_in_original_run"] == 0
    assert limits["controlled_conditions_varied"] is False
    assert limits["future_trial_values_in_input"] is False
    assert limits["physical_online_proposal"] is False
    assert limits["original_paper_sha256"] == data["original_artifact"]["paper_stdout_sha256"]


def test_real_original_g3_negatives_preserved_not_reclassified():
    trials = parse_g3_readback(original())
    assert len(trials) == 3
    assert [t.wait_first_tick for t in trials] == [299, 499, 699]
    assert all(
        t.fixed_slope_next_motion_mae_m > t.cheap_zero_next_motion_mae_m
        for t in trials
    )
    assert trials[0].observed_wait_total_m != trials[1].observed_wait_total_m
    assert trials[1].observed_wait_total_m == pytest.approx(
        trials[2].observed_wait_total_m
    )
    assert all(not t.physical_cause_identified for t in trials)


def test_fake_l2_reads_only_prefix_and_creates_unexecuted_hypothesis():
    for n in [0, 1, 2]:
        prefix = freeze_archived_prefix(original(), visible_count=n)
        p = shadow_l2_preview(prefix, fake_result)
        assert p.visible_count == n
        assert p.referenced_prior_ordinals == tuple(range(1, n+1))
        assert p.reconsideration == [
            "KEEP_UNRESOLVED", "QUESTION_APPLICABILITY", "PROPOSE_STRUCTURAL_REVISION",
        ][n]
        assert p.source_status.endswith("UNTESTED")
        assert p.provider_source == "fake.fixture"
        assert not p.executable_action and not p.world_mutation_allowed
        assert p.learning_admissions == p.l0_promotions == 0
        assert len(p.proposal_sha256) == 64


def test_real_relayengine_open_api_fake_provider_call_not_real_gemma():
    calls = []
    def provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        calls.append(req.request_id)
        fake = fake_result(req)
        return ProviderExpression(
            text=fake.text, provenance=Provenance("fake.relayengine", "offline"),
        )
    engine = RelayEngine(provider)
    prefix = freeze_archived_prefix(original(), visible_count=2)
    p = shadow_l2_preview(prefix, engine.open)
    assert calls == [make_l2_request(prefix).request_id]
    assert p.provider_source == "fake.relayengine"
    assert p.reconsideration == "PROPOSE_STRUCTURAL_REVISION"
    assert p.source_status == "ARCHIVED_G3_L2_SHADOW_HYPOTHESIS_UNTESTED"


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(github_run=123),
    lambda d: d["original_artifact"].update(paper_stdout_sha256="a"*64),
    lambda d: d["original_artifact"].update(node_stdout_sha256="b"*64),
    lambda d: d["independent_review"].update(no_s15_duplicate_or_s16_unknown=False),
    lambda d: d["source_binding"].update(real_gemma_calls=1),
    lambda d: d["source_binding"].update(learning_admission_count=1),
    lambda d: d["source_binding"].update(all_surfaces="PACKED_ICE"),
    lambda d: d["source_binding"].update(original_s16_outcome_count=2),
    lambda d: d["trials"][1].update(action_id="foreign"),
    lambda d: d["trials"][1].update(paper_wait_ticks=[302, 309]),
    lambda d: d["trials"][0].update(prequential_mae_m=0.0001),
    lambda d: d["trials"][0].update(wait8_total_m=float("nan")),
    lambda d: d["trials"][0].update(first_wait_displacement_m=999.0),
    lambda d: d["evidence_limits"].update(qualification="GO"),
    lambda d: d["evidence_limits"].update(science="PASS"),
])
def test_wrong_stale_overstated_archived_evidence_fails_closed(mutate):
    data = deepcopy(original())
    mutate(data)
    with pytest.raises(G3PrefixRejected):
        freeze_archived_prefix(data, visible_count=1)


@pytest.mark.parametrize("count", [-1, 3, 4, 1.0, True])
def test_full_postrun_future_never_replayed_as_prior_visible(count):
    with pytest.raises(G3PrefixRejected):
        freeze_archived_prefix(original(), visible_count=count)


def test_fake_archived_prefix_cannot_upgrade_qualification():
    prefix = freeze_archived_prefix(original(), visible_count=1)
    for forged in [
        replace(prefix, physically_online_at_prefix=True),
        replace(prefix, original_bytes_reauthenticated=True),
        replace(prefix, source_status="LIVE_REAL_WORLD_QUALIFIED"),
        replace(prefix, report_sha256="not-a-hash"),
        replace(prefix, visible_count=2),
        replace(prefix, previous_trials=prefix.previous_trials + prefix.previous_trials),
        replace(prefix, previous_trials=(replace(
            prefix.previous_trials[0], input_duration_variation_proven=True,
        ),)),
    ]:
        with pytest.raises(G3PrefixRejected):
            make_l2_request(forged)


@pytest.mark.parametrize("bad", [
    "missing_provider", "not_json", "array", "extra_command", "future_ordinal",
    "duplicate_prior", "unsorted_prior", "invalid_family", "invalid_test",
    "invalid_revision", "unsupported_revision", "unbounded_prediction",
    "nan_prediction", "short_explanation", "stale_request", "wrong_type",
    "unhashable_family",
])
def test_open_l2_hypothesis_schema_and_prior_scope_denials(bad):
    prefix = freeze_archived_prefix(original(), visible_count=1)
    if bad == "missing_provider":
        with pytest.raises(G3PrefixRejected):
            shadow_l2_preview(prefix, None)
        return
    def provider(req):
        ans = fake_result(req)
        raw = json.loads(ans.text)
        if bad == "not_json":
            return replace(ans, text="{not-json")
        if bad == "array":
            return replace(ans, text="[]")
        if bad == "extra_command":
            raw["minecraft_command"] = "give op"
        elif bad == "future_ordinal":
            raw["referenced_prior_ordinals"] = [2]
        elif bad == "duplicate_prior":
            raw["referenced_prior_ordinals"] = [1, 1]
        elif bad == "unsorted_prior":
            raw["referenced_prior_ordinals"] = [2, 1]
        elif bad == "invalid_family":
            raw["model_family"] = "RUN_PYTHON"
        elif bad == "invalid_test":
            raw["next_test"] = "CHANGE_WORLD_UNBOUNDED"
        elif bad == "invalid_revision":
            raw["reconsideration"] = "AUTO_PROMOTE_L0"
        elif bad == "unsupported_revision":
            raw["referenced_prior_ordinals"] = []
        elif bad == "unbounded_prediction":
            raw["predicted_wait_total_m"] = 99
        elif bad == "nan_prediction":
            raw["predicted_wait_total_m"] = float("nan")
        elif bad == "short_explanation":
            raw["explanation"] = "x"
        elif bad == "stale_request":
            return replace(ans, request_id="wrong")
        elif bad == "wrong_type":
            return object()
        elif bad == "unhashable_family":
            raw["model_family"] = ["RUN"]
        return replace(ans, text=json.dumps(raw))
    with pytest.raises(G3PrefixRejected):
        shadow_l2_preview(prefix, provider)
