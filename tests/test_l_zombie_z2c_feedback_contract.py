"""Z2c H2 feedback tests. Simulated HTTP never proves a real Gemma run."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from adapters.mineflayer.l_zombie_z2b_policy_contract import _canonical
from adapters.mineflayer.l_zombie_z2c_feedback_contract import (
    ISSUES,
    SOURCE_IDS,
    TARGET,
    ZombiePolicyRejected,
    build_request,
    freeze_h2,
    revision_json,
    schema,
    validate_h2,
)
from tools import l_zombie_z2c_h2_original_feedback as tool

H1_SHA = "5ab25d00180e72b739474f4aaca93317421b2f275975cb737775b7061dbde4ed"
PAPER_SHA = "1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815"
SOURCE_ROOT = Path("docs/evidence/l-z2b-real-20261102")


def old():
    return {
        "strategy": "STATIONARY", "speed_m_per_tick": None,
        "applicability": "CONDITIONS_UNRESOLVED",
        "policy_sha256": H1_SHA,
        "reason": (
            "Limited evidence; chase_causality is NOT_ATTESTED and no current "
            "player coordinates are available for TARGET_APPROACH."
        ),
        "falsification_test": (
            "If zombie moves > 1.5m from start_xz_m, then "
            "CONSTANT_VELOCITY is false."
        ),
    }


def world():
    return {
        "strategy": "STATIONARY", "policy_sha256": H1_SHA,
        "original_paper_sha256": PAPER_SHA,
        "world_uuid": "0c73cad5-ad84-4112-a708-4a1fb9ff9fc4",
        "zombie_uuid": "1427da04-3095-4045-93b1-74a8f9d17b8f",
        "issued_tick": 37, "target_tick": 57,
        "frozen_before_next_tick": True,
        "model_live_in_world_calls": 0,
        "model_prepared_xz_m": [-2.5, -1.5],
        "future_actual_xz_m": [-3.983553173838, -1.525954708854],
        "cheap_stationary_error_m": 1.4837801948120548,
        "cheap_velocity_error_m": 1.4837801948120548,
    }


def answer(**changes):
    result = {
        "measurement_target": TARGET,
        "evaluated_prior_strategy": "STATIONARY",
        "observed_horizontal_error_m": 1.4838,
        "error_basis": "ORIGINAL_PAPER_EXACT_TICK_XZ",
        "old_falsification_named_strategy": "CONSTANT_VELOCITY",
        "diagnosed_issues": [
            "OLD_FALSIFICATION_NAMES_OTHER_RULE",
            "PREPARATION_VS_WORLD_FREEZE_COORDINATES_CONFUSED",
            "CHASE_CAUSALITY_UNATTESTED",
        ],
        "cheap_relation": "TIED",
        "reconsideration": "RESTRICT_APPLICABILITY",
        "proposed_strategy": "STATIONARY",
        "proposed_speed_m_per_tick": None,
        "proposed_applicability": "DO_NOT_APPLY_STATIONARY_WHEN_TARGET_APPROACH_OBSERVED",
        "next_falsification_target": "STATIONARY",
        "next_test_error_threshold_m": 0.5,
        "next_falsification_test": (
            "In a separate future exact +20 tick Paper trajectory, reject "
            "STATIONARY if its horizontal prediction error exceeds 0.5 m."
        ),
        "rationale": (
            "The prior strategy was STATIONARY but its falsification named "
            "CONSTANT_VELOCITY. The old model lacked future player inputs "
            "at preparation, although Paper can observe them at freeze time."
        ),
        "evidence_ids": list(SOURCE_IDS),
    }
    result.update(changes)
    return result


def reply(value=None, *, finish="stop", reasoning=None):
    msg = {"role": "assistant", "content": json.dumps(
        value if value is not None else answer(),
    )}
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    return _canonical({
        "choices": [{"finish_reason": finish, "message": msg}],
        "usage": {"completion_tokens_details": {"reasoning_tokens": 0}},
    })


def frozen(value=None):
    body = build_request(
        model="relay-self-gemma4-12b-q4km",
        old_policy=old(), completed_world=world(),
        paper_original_sha256=PAPER_SHA,
    )
    return freeze_h2(
        request_raw=_canonical(body), response_raw=reply(value),
        expected_request=body, old_policy=old(), world=world(),
    )


def test_exact_h2_schema_source_feedback_and_no_precomputed_error_leak():
    result = schema()
    assert result["json_schema"]["strict"] is True
    assert result["json_schema"]["schema"]["additionalProperties"] is False
    body = build_request(
        model="relay-self-gemma4-12b-q4km",
        old_policy=old(), completed_world=world(),
        paper_original_sha256=PAPER_SHA,
    )
    assert body["reasoning_effort"] == "none"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["cache_prompt"] is False and body["stream"] is False
    assert body["response_format"] == result
    ctx = json.loads(body["messages"][1]["content"])
    assert ctx["epoch"] == "AFTER_Z2B_WORLD_COMPLETED_NO_NEXT_WORLD"
    assert ctx["old_policy"]["strategy"] == "STATIONARY"
    assert "CONSTANT_VELOCITY" in ctx["old_policy"]["falsification_test"]
    assert ctx["world_source"]["issued_tick"] == 37
    assert ctx["world_source"]["target_tick"] == 57
    assert ctx["world_source"]["original_actual_xz_m"] == world()["future_actual_xz_m"]
    assert "observed_error_m" not in json.dumps(ctx)
    assert "1.4837801948120548" not in json.dumps(ctx)
    assert not any("next_world_future" in x for x in ctx)


def test_exact_original_error_and_contradiction_diagnosis_freezes_only_proposal():
    r = frozen()
    assert r.observed_error_m == 1.4838
    assert r.reconsideration == "RESTRICT_APPLICABILITY"
    assert r.proposed_strategy == "STATIONARY"
    assert r.next_falsification_target == "STATIONARY"
    assert set(ISSUES[:2]).issubset(r.diagnosed_issues)
    assert r.original_h1_policy_sha256 == H1_SHA
    assert r.paper_original_sha256 == PAPER_SHA
    assert len(r.revision_sha256) == 64
    assert r.learning_authorized is False
    assert r.action_authorized is False
    assert r.qualification_go is False
    assert json.loads(revision_json(r))["classification"] == (
        "H2_SOURCE_BOUND_PROPOSED_NOT_ADMITTED"
    )
    assert r.revision_sha256 == frozen().revision_sha256


@pytest.mark.parametrize("changes", [
    {"observed_horizontal_error_m": 0.0},
    {"observed_horizontal_error_m": 1.55},
    {"observed_horizontal_error_m": "1.4838"},
    {"observed_horizontal_error_m": True},
    {"observed_horizontal_error_m": float("nan")},
    {"evaluated_prior_strategy": "CONSTANT_VELOCITY"},
    {"old_falsification_named_strategy": "STATIONARY"},
    {"cheap_relation": "BETTER_THAN_BOTH"},
    {"error_basis": "CLIENT_SEQ_DURATION"},
    {"diagnosed_issues": ["CHASE_CAUSALITY_UNATTESTED"]},
    {"diagnosed_issues": [
        "OLD_FALSIFICATION_NAMES_OTHER_RULE",
        "OLD_FALSIFICATION_NAMES_OTHER_RULE",
    ]},
    {"proposed_strategy": "TARGET_APPROACH", "proposed_speed_m_per_tick": None},
    {"proposed_strategy": "STATIONARY", "proposed_speed_m_per_tick": 0.1},
    {"reconsideration": "PROPOSE_ALTERNATIVE", "proposed_strategy": "STATIONARY"},
    {"reconsideration": "KEEP_WITH_LIMITS", "proposed_strategy": "TARGET_APPROACH",
     "proposed_speed_m_per_tick": 0.11, "next_falsification_target": "TARGET_APPROACH"},
    {"reconsideration": "ABSTAIN_PENDING_MORE_EVIDENCE", "proposed_strategy": "STATIONARY"},
    {"proposed_strategy": "ABSTAIN", "next_falsification_target": "ABSTAIN"},
    {"next_falsification_target": "CONSTANT_VELOCITY"},
    {"next_test_error_threshold_m": 0.0},
    {"next_test_error_threshold_m": 5.5},
    {"next_falsification_test": "If zombie moves > 1.5m old model false."},
    {"evidence_ids": ["Z2B_ORIGINAL_PAPER_T37_T57"]},
    {"rationale": "too short"},
    {"extra": "unapproved"},
])
def test_invalid_numeric_qualitative_and_future_proposal_rejected(changes):
    with pytest.raises(ZombiePolicyRejected):
        validate_h2(answer(**changes), prior=old(), world=world())


def test_valid_alternative_and_abstention_remain_unadmitted():
    x = answer(
        reconsideration="PROPOSE_ALTERNATIVE",
        proposed_strategy="TARGET_APPROACH",
        proposed_speed_m_per_tick=0.11,
        next_falsification_target="TARGET_APPROACH",
    )
    validate_h2(x, prior=old(), world=world())
    x = answer(
        reconsideration="ABSTAIN_PENDING_MORE_EVIDENCE",
        proposed_strategy="ABSTAIN",
        next_falsification_target="STATIONARY",
        proposed_applicability="CONDITIONS_UNRESOLVED",
    )
    validate_h2(x, prior=old(), world=world())
    assert frozen(x).learning_authorized is False


def test_duplicate_inner_json_key_truncation_or_reasoning_contamination_rejected():
    body = build_request(
        model="relay-self-gemma4-12b-q4km",
        old_policy=old(), completed_world=world(), paper_original_sha256=PAPER_SHA,
    )
    wire = json.loads(reply())
    wire["choices"][0]["message"]["content"] = json.dumps(answer()).replace(
        '"rationale":', '"rationale": "duplicate", "rationale":',
    )
    for raw in (_canonical(wire), reply(finish="length"), reply(reasoning="hidden")):
        with pytest.raises(ZombiePolicyRejected):
            freeze_h2(
                request_raw=_canonical(body), response_raw=raw,
                expected_request=body, old_policy=old(), world=world(),
            )


def test_wrong_request_model_or_modified_original_prediction_rejected():
    body = build_request(
        model="relay-self-gemma4-12b-q4km", old_policy=old(),
        completed_world=world(), paper_original_sha256=PAPER_SHA,
    )
    with pytest.raises(ZombiePolicyRejected):
        freeze_h2(
            request_raw=_canonical(body)+b" ",
            response_raw=reply(), expected_request=body,
            old_policy=old(), world=world(),
        )
    fake = dict(world())
    fake["target_tick"] = 56
    with pytest.raises(ZombiePolicyRejected):
        build_request(
            model="relay-self-gemma4-12b-q4km",
            old_policy=old(), completed_world=fake,
            paper_original_sha256=PAPER_SHA,
        )


def test_saved_68_file_original_replay_works_without_new_world_or_gemma():
    root = SOURCE_ROOT.resolve()
    policy, physical, receipt = tool.original_z2b_h2_sources(root)
    assert policy["policy_sha256"] == H1_SHA
    assert physical["original_paper_sha256"] == PAPER_SHA
    assert physical["issued_tick"] == 37 and physical["target_tick"] == 57
    assert physical["prepared_policy_error_m"] == pytest.approx(1.4837801948120548)
    assert receipt["new_model_calls"] == receipt["new_worlds"] == 0
    assert receipt["archived_files_checked"] >= 68
    body = build_request(
        model="relay-self-gemma4-12b-q4km", old_policy=policy,
        completed_world=physical, paper_original_sha256=PAPER_SHA,
    )
    assert body["response_format"] == schema()


def test_http_single_request_journaling_with_synthetic_response(tmp_path, monkeypatch):
    monkeypatch.setenv("L_ZOMBIE_Z2C_REAL_H2_DEV", "1")
    monkeypatch.setattr(
        tool, "original_z2b_h2_sources",
        lambda root: (old(), world(), {
            "classification": "SAVED_Z2B_ORIGINAL_REPLAY_PASS_NOT_LIVE_ATTESTATION",
            "archived_files_checked": 68,
        }),
    )
    class FakeResponse(io.BytesIO):
        pass

    calls = []
    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        return FakeResponse(reply())
    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)
    output = tmp_path / "one-h2-original"
    value = tool.real_h2_once(
        original_root=tmp_path, output_root=output,
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="relay-self-gemma4-12b-q4km",
    )
    assert value["status"] == "H2_CONTRACT_DEV_PASS_UNADMITTED"
    assert len(calls) == 1
    assert (output / "h2-request-1.raw.json").exists()
    assert (output / "h2-response-1.raw.json").read_bytes() == reply()
    assert (output / "h2-revision-proposal-v1.json").exists()
    status = json.loads((output / "h2-status.json").read_text())
    assert status["h2_http_requests_max"] == 1
    assert status["h2_worlds"] == 0
    assert not (tmp_path/"world").exists()
    with pytest.raises(ZombiePolicyRejected, match="unique new"):
        tool.real_h2_once(
            original_root=tmp_path, output_root=output,
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="relay-self-gemma4-12b-q4km",
        )


def test_failing_one_http_keeps_original_request_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("L_ZOMBIE_Z2C_REAL_H2_DEV", "1")
    monkeypatch.setattr(tool, "original_z2b_h2_sources",
                        lambda root: (old(), world(), {}))
    monkeypatch.setattr(tool.urllib.request, "urlopen",
                        lambda req, timeout: io.BytesIO(reply(finish="length")))
    output = tmp_path / "failed-h2"
    with pytest.raises(ZombiePolicyRejected):
        tool.real_h2_once(
            original_root=tmp_path, output_root=output,
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="relay-self-gemma4-12b-q4km",
        )
    assert (output / "h2-request-1.raw.json").exists()
    assert (output / "h2-response-1.raw.json").exists()
    assert json.loads((output / "h2-status.json").read_text())["status"] == (
        "H2_NOT_ESTABLISHED"
    )
    assert not (output / "h2-revision-proposal-v1.json").exists()
