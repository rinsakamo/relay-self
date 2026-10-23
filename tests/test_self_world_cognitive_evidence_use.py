"""DEV source-only evidence-use gate: no provider or physical execution."""
from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from experiments import self_world_cognitive_evidence_use as gate
from experiments import self_world_host_two_axis as host
from experiments.self_world_metadata_ablation import digest
from test_self_world_host_two_axis import sources as verified_sources


@pytest.fixture
def sources(tmp_path, monkeypatch):
    return verified_sources.__wrapped__(tmp_path, monkeypatch)


def prepare(sources, monkeypatch, case=2, epoch="following", goal=None,
            claimed_record=None, digest_override=None):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    c, replay = sources[case]
    return gate.prepare_evidence_use(
        None, case_id=c.case_id, epoch=epoch,
        expected_source_digest=digest_override or digest(asdict(replay)),
        goal=goal, claimed_record=claimed_record,
    )


def goal(kind="EXPLAIN_OBSERVED", budget=0.5):
    return gate.GoalSpec(kind, 2, budget)


@pytest.mark.parametrize("kind,budget", [
    ("EXPLAIN_OBSERVED", 0.0),
    ("ASSESS_FORECAST", 0.5),
])
def test_ten_epochs_goals_stay_host_bound(sources, monkeypatch, kind, budget):
    expected = [
        (0, "NO_REVIEW", False, False),
        (0, "NO_REVIEW", False, False),
        (1, "NO_REVIEW", True, False),
        (1, "MATCH", True, True),
        (1, "NO_REVIEW", True, False),
        (1, "MISMATCH", True, False),
        (1, "NO_REVIEW", True, False),
        (0, "UNDETERMINED", False, False),
        (0, "NO_REVIEW", False, False),
        (0, "NO_REVIEW", False, False),
    ]
    results = [
        prepare(sources, monkeypatch, i, epoch, goal(kind, budget))
        for i in range(5) for epoch in ("prior", "following")
    ]
    for i, r in enumerate(results):
        positive, review, current_ok, match_ok = expected[i]
        assert ("USE_CURRENT_POSITIVE" in r.admissible) is current_ok
        assert ("USE_MATCHED_FORECAST_SCOPE" in r.admissible) is match_ok
        assert r.custody_manifest["source_digest"] == digest(asdict(sources[i // 2][1]))
        assert r.scope == gate.SCOPE
        assert (r.model_calls, r.world_actions, r.memory_writes, r.s10_updates) == (
            0, 0, 0, 0,
        )
        if r.status == "READY":
            assert r.request is not None
            assert len(r.request.choices) >= 2
            assert tuple(c.choice_id for c in r.request.choices) == r.available
            assert r.request_sha256 == digest(asdict(r.request))
            projected = {
                d.key: __import__("json").loads(d.value_json) for d in r.request.context
            }
            assert projected["dev_host_evidence_allowlist"]["positive_selected_count"] == positive
            assert projected["dev_host_evidence_allowlist"]["review_status"] == review
        else:
            assert budget == 0.0 and positive == 0
            assert r.request is None
            assert r.available == ("WITHHOLD_UNSUPPORTED_CLAIM",)


def test_mismatch_keeps_current_skeleton_without_old_zombie(sources, monkeypatch):
    r = prepare(sources, monkeypatch, goal=goal("ASSESS_FORECAST"))
    assert "USE_CURRENT_POSITIVE" in r.admissible
    assert "USE_MATCHED_FORECAST_SCOPE" not in r.admissible
    assert gate.validate_selected_strategy(
        r, choice_id="USE_CURRENT_POSITIVE", request_sha256=r.request_sha256,
    ) == "USE_CURRENT_POSITIVE"
    p = __import__("json").loads(r.request.context[1].value_json)
    assert p["current_positive"][0]["label"] == "skeleton"
    assert p["matched_scope"] is None
    assert p["review_status"] == "MISMATCH"
    assert not any("zombie" in str(x) for x in p["current_positive"])


def test_match_is_only_current_target_attribute_scope(sources, monkeypatch):
    r = prepare(sources, monkeypatch, case=1, goal=goal("ASSESS_FORECAST"))
    assert "USE_MATCHED_FORECAST_SCOPE" in r.available
    p = __import__("json").loads(r.request.context[1].value_json)
    assert p["matched_scope"] == {
        "property": "entity_label",
        "supported_value": "zombie",
        "scope": "observed_target_only",
    }


def test_prior_forecast_no_review_not_promoted(sources, monkeypatch):
    r = prepare(sources, monkeypatch, case=1, epoch="prior", goal=goal())
    p = __import__("json").loads(r.request.context[1].value_json)
    assert p["prior_forecast_present"]
    assert p["forecast_present_in_view"]
    assert p["review_status"] == "NO_REVIEW"
    assert p["matched_scope"] is None
    assert "USE_CURRENT_POSITIVE" in r.available
    assert "USE_MATCHED_FORECAST_SCOPE" not in r.available


def test_unknown_following_is_not_false_forecast_or_world_absence(sources, monkeypatch):
    r = prepare(sources, monkeypatch, case=3, goal=goal())
    p = __import__("json").loads(r.request.context[1].value_json)
    assert p["review_status"] == "UNDETERMINED"
    assert p["positive_selected_count"] == 0
    assert p["unobserved"] == "UNKNOWN_not_world_absence"
    assert p["prior_forecast_present"]
    assert p["matched_scope"] is None
    assert "USE_MATCHED_FORECAST_SCOPE" not in r.admissible


def test_no_goal_or_zero_budget_is_defer_when_only_one_choice(sources, monkeypatch):
    for g in (None, goal(budget=0.0)):
        r = prepare(sources, monkeypatch, case=0, goal=g)
        assert r.status == "DEFER"
        assert r.request is None
        with pytest.raises(gate.EvidenceUseBlocked):
            gate.validate_selected_strategy(
                r, choice_id="WITHHOLD_UNSUPPORTED_CLAIM", request_sha256="",
            )


@pytest.mark.parametrize("bad", [
    ("EXPLAIN_OBSERVED", 1, -1),
    ("EXPLAIN_OBSERVED", 1, float("nan")),
    ("EXPLAIN_OBSERVED", 1, float("inf")),
    ("EXPLAIN_OBSERVED", 0, 1),
    ("EXPLAIN_OBSERVED", True, 1),
    ("FORGED_SOURCE_GOAL", 1, 1),
])
def test_bad_goals_rejected(bad):
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.GoalSpec(*bad)


def test_cannot_force_candidate_or_replay_request(sources, monkeypatch):
    r = prepare(sources, monkeypatch, goal=goal())
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.validate_selected_strategy(
            r, choice_id="USE_MATCHED_FORECAST_SCOPE", request_sha256=r.request_sha256,
        )
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.validate_selected_strategy(
            r, choice_id="USE_CURRENT_POSITIVE", request_sha256="0" * 64,
        )
    forged = replace(r, available=(*r.available, "USE_MATCHED_FORECAST_SCOPE"))
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.validate_selected_strategy(
            forged, choice_id="USE_MATCHED_FORECAST_SCOPE",
            request_sha256=forged.request_sha256,
        )
    tampered_request = replace(r.request, request_id="foreign-replay")
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.validate_selected_strategy(
            replace(r, request=tampered_request),
            choice_id="USE_CURRENT_POSITIVE", request_sha256=r.request_sha256,
        )


@pytest.mark.parametrize("attack", [
    "bad_digest", "foreign_self", "foreign_epoch", "false_absence",
    "changed_positive", "changed_review", "bad_att", "same_semantics_foreign_source",
])
def test_claimed_record_never_substitutes_fresh_verified_source(
    sources, monkeypatch, attack,
):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    c, replay = sources[2]
    pin = digest(asdict(replay))
    original = host.read_epoch(None, case_id=c.case_id, epoch="following",
                               expected_source_digest=pin)
    forged = deepcopy(original)
    if attack == "bad_digest":
        forged["observation"]["source_bound_digest"] = "0" * 64
    elif attack == "foreign_self":
        forged["binding"]["self_id"] = "foreign"
    elif attack == "foreign_epoch":
        forged["binding"]["epoch_id"] = "wrong"
    elif attack == "false_absence":
        forged["observation"]["world_absence_established"] = True
    elif attack == "changed_positive":
        forged["observation"]["selected_positive_observations"][0]["label"] = "zombie"
    elif attack == "changed_review":
        forged["prediction"]["review_status"] = "MATCH"
    elif attack == "bad_att":
        forged["observation"]["attention"] = {"selected": []}
    elif attack == "same_semantics_foreign_source":
        forged["binding"]["session_id"] = "copy-with-same-observation"
    with pytest.raises(gate.EvidenceUseBlocked):
        prepare(sources, monkeypatch, goal=goal(), claimed_record=forged)


def test_original_receipt_pin_rejected(sources, monkeypatch):
    with pytest.raises(ValueError):
        prepare(sources, monkeypatch, goal=goal(), digest_override="0" * 64)


def test_tampered_host_axis_digest_rejected_even_without_claim(sources, monkeypatch):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    c, replay = sources[1]
    pin = digest(asdict(replay))
    record = host.read_epoch(None, case_id=c.case_id, epoch="following",
                             expected_source_digest=pin)
    record["prediction"]["source_bound_review_digest"] = "0" * 64
    with pytest.raises(gate.EvidenceUseBlocked):
        gate._checked_record(record, pin)


def test_match_target_or_attribute_cannot_be_swapped(sources, monkeypatch):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    c, replay = sources[1]
    pin = digest(asdict(replay))
    record = host.read_epoch(None, case_id=c.case_id, epoch="following",
                             expected_source_digest=pin)
    for key, change in (("target_ref", "other"), ("variable_key", "visible_action")):
        forged = deepcopy(record)
        forged["prediction"]["review"][key] = change
        p = forged["prediction"]
        p.pop("source_bound_review_digest")
        p["source_bound_review_digest"] = digest({
            "binding": forged["binding"], "prediction": p,
        })
        with pytest.raises(gate.EvidenceUseBlocked):
            gate.prepare_evidence_use(
                None, case_id=c.case_id, epoch="following",
                expected_source_digest=pin, goal=goal(), claimed_record=forged,
            )


def test_projection_never_leaks_host_custody_or_raw_identity(sources, monkeypatch):
    r = prepare(sources, monkeypatch, goal=goal())
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    c, replay = sources[2]
    original = host.read_epoch(
        None, case_id=c.case_id, epoch="following",
        expected_source_digest=digest(asdict(replay)),
    )
    request = asdict(r.request)
    rendered = __import__("json").dumps(request)
    protected = [
        original["binding"]["source_receipt_sha256"],
        original["binding"]["self_id"],
        original["binding"]["session_id"],
        original["binding"]["epoch_id"],
        original["observation"]["observation_source"]["source_ref"],
        original["observation"]["selected_positive_observations"][0]["entity_ref"],
        original["observation"]["source_bound_digest"],
    ]
    assert all(x not in rendered for x in protected)
    for bad in ("source_receipt_sha256", "entity_ref", "world_absence_established",
                "world_safety_established", "source_bound_digest"):
        assert bad not in rendered
    assert r.custody_manifest["source_digest"] not in rendered
