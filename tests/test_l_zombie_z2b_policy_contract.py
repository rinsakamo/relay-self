"""All Z2b policy samples here are SYNTHETIC -- no real Gemma call."""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    APPLICABILITY,
    EVIDENCE_IDS,
    EXPECTED_PRIOR_SHA,
    STRATEGIES,
    TARGET,
    ZombiePolicyRejected,
    _canonical,
    freeze_from_http,
    policy_json,
    prediction_from_prior,
    request,
    schema,
    validate_selection,
)
from tools import l_zombie_z2b_prepare_gemma as tool


def priors():
    return tuple({
        "source_scope": "COMPLETED_PREVIOUS_WORLD",
        "raw_original_sha256": sha,
        "zombie_uuid": f"prior-zombie-{i}",
        "start_xz_m": [10.5, 7.5],
        "end_xz_m": [8.3, 7.5],
    } for i, sha in enumerate(EXPECTED_PRIOR_SHA))


def selection(**updates):
    out = {
        "measurement_target": TARGET,
        "strategy": "TARGET_APPROACH",
        "speed_m_per_tick": 0.11,
        "applicability": "SINGLE_VISIBLE_TARGET_OPEN_GROUND",
        "reason": "Two earlier Paper episodes show movement after a prior idle phase.",
        "falsification_test": "Recheck different starting player distance and obstacle with held-out evidence.",
        "evidence_ids": ["Z1B_T40_T60", "Z2A_T46_T66"],
    }
    out.update(updates)
    return out


def payload(choice=None, *, finish_reason="stop", reasoning=None):
    message = {"role": "assistant", "content": json.dumps(choice or selection())}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return _canonical({
        "choices": [{"finish_reason": finish_reason, "message": message}],
        "usage": {"completion_tokens_details": {"reasoning_tokens": 0}},
    })


def frozen(**updates):
    req = request("Gemma-real-model-alias", original_prior=priors())
    return freeze_from_http(
        original_request=_canonical(req),
        original_response=payload(selection(**updates)),
        expected_request=req,
    )


def test_model_schema_native_and_no_world_wait():
    s = schema()
    assert s["type"] == "json_schema" and s["json_schema"]["strict"] is True
    assert not s["json_schema"]["schema"]["additionalProperties"]
    assert len(s["json_schema"]["schema"]["required"]) == 7
    r = request("Gemma-real-model-alias", original_prior=priors())
    assert r["reasoning_effort"] == "none"
    assert r["chat_template_kwargs"] == {"enable_thinking": False}
    assert r["stream"] is False and r["cache_prompt"] is False
    assert r["response_format"] == s and r["max_tokens"] == 384
    assert all(x in STRATEGIES for x in ("TARGET_APPROACH", "ABSTAIN"))
    assert len(APPLICABILITY) == 2 and len(EVIDENCE_IDS) == 2
    ctx = json.loads(r["messages"][1]["content"])
    assert ctx["prior_experiences"][0]["raw_original_sha256"] == EXPECTED_PRIOR_SHA[0]
    assert ctx["prior_experiences"][1]["raw_original_sha256"] == EXPECTED_PRIOR_SHA[1]
    assert "future_world_zombie_position" not in ctx


def test_prepared_real_http_shape_freezes_hash_and_conditional_point():
    p = frozen()
    assert p.strategy == "TARGET_APPROACH" and p.speed_m_per_tick == 0.11
    assert p.no_action_authority and p.no_learning_admission
    assert p.source_kind == "PREPARED_L2_POLICY_UNADMITTED_V1"
    assert p.prior_source_sha256 == EXPECTED_PRIOR_SHA
    p2 = frozen()
    assert p2.policy_sha256 == p.policy_sha256
    assert json.loads(policy_json(p))["policy_sha256"] == p.policy_sha256
    # Old-world L2 rule now conditions on *future* World pre-outcome positions.
    # x=10, target player x=6; 20*.11=2.2, so predicted x=7.8.
    assert prediction_from_prior(
        p, first_xz=(10.0, 0.0), issued_xz=(10.0, 0.0),
        player_xz=(6.0, 0.0),
    ) == pytest.approx((7.8, 0.0))


def test_stopped_and_velocity_and_abstain_are_not_fake_gemma_skill():
    shared = dict(first_xz=(0, 0), issued_xz=(1, 0), player_xz=(4, 0))
    assert prediction_from_prior(
        frozen(strategy="STATIONARY", speed_m_per_tick=None), **shared,
    ) == (1, 0)
    assert prediction_from_prior(
        frozen(strategy="CONSTANT_VELOCITY", speed_m_per_tick=None), **shared,
    ) == (3, 0)
    assert prediction_from_prior(
        frozen(strategy="ABSTAIN", speed_m_per_tick=None), **shared,
    ) is None


@pytest.mark.parametrize("change", [
    {"measurement_target": "NEXT_WAIT8_DURATION_MS"},
    {"strategy": "UNSUPPORTED"},
    {"strategy": "ABSTAIN", "speed_m_per_tick": 0.1},
    {"strategy": "STATIONARY", "speed_m_per_tick": 0.1},
    {"strategy": "TARGET_APPROACH", "speed_m_per_tick": None},
    {"strategy": "TARGET_APPROACH", "speed_m_per_tick": True},
    {"strategy": "TARGET_APPROACH", "speed_m_per_tick": 0.31},
    {"strategy": "TARGET_APPROACH", "speed_m_per_tick": float("nan")},
    {"applicability": "ALWAYS_VALID"},
    {"reason": "too short"},
    {"falsification_test": "bad"},
    {"evidence_ids": ["Z9_FUTURE"]},
    {"evidence_ids": ["Z1B_T40_T60", "Z1B_T40_T60"]},
])
def test_invalid_strategy_or_future_claim_fails_closed(change):
    with pytest.raises(ZombiePolicyRejected):
        validate_selection(selection(**change))


@pytest.mark.parametrize("finish,reasoning", [
    ("length", None), ("stop", "model hidden reasoning"),
])
def test_model_truncation_or_reasoning_leak_fails(finish, reasoning):
    req = request("Gemma-real-model-alias", original_prior=priors())
    with pytest.raises(ZombiePolicyRejected):
        freeze_from_http(
            original_request=_canonical(req),
            original_response=payload(finish_reason=finish, reasoning=reasoning),
            expected_request=req,
        )


def test_request_tampering_prior_sha_and_response_duplicate_key_fails():
    req = request("Gemma-real-model-alias", original_prior=priors())
    with pytest.raises(ZombiePolicyRejected, match="request changed"):
        freeze_from_http(
            original_request=_canonical(req) + b" ",
            original_response=payload(),
            expected_request=req,
        )
    fake = dict(req)
    fake["chat_template_kwargs"] = {"enable_thinking": True}
    with pytest.raises(ZombiePolicyRejected, match="protocol"):
        freeze_from_http(
            original_request=_canonical(fake),
            original_response=payload(),
            expected_request=fake,
        )
    response = payload().replace(b'"reason":', b'"reason":"duplicate", "reason":')
    with pytest.raises(ZombiePolicyRejected):
        freeze_from_http(
            original_request=_canonical(req),
            original_response=response,
            expected_request=req,
        )
    bad = priors()
    bad = (dict(bad[0], raw_original_sha256="0"*64), bad[1])
    with pytest.raises(ZombiePolicyRejected):
        request("Gemma-real-model-alias", original_prior=bad)


def test_policy_math_rejects_bad_input_and_never_promotes_l0():
    p = frozen()
    for value in (
        dict(first_xz=(float("nan"), 0), issued_xz=(1, 0), player_xz=(3, 0)),
        dict(first_xz=(0, 0), issued_xz=(1,), player_xz=(3, 0)),
        dict(first_xz=(0, 0), issued_xz=(1, 0), player_xz=(3, 0), prior_ticks=0),
    ):
        with pytest.raises(ZombiePolicyRejected):
            prediction_from_prior(p, **value)
    p = replace(p, strategy="ABSTAIN", speed_m_per_tick=None)
    assert prediction_from_prior(
        p, first_xz=(0, 0), issued_xz=(1, 0), player_xz=(2, 0),
    ) is None


@pytest.mark.parametrize("endpoint", [
    "https://127.0.0.1:8080/v1/chat/completions",
    "http://openai.com:8080/v1/chat/completions",
    "http://192.168.0.2:8080/v1/chat/completions",
    "http://127.0.0.1:8080/other",
    "http://127.0.0.1:8080/v1/chat/completions?auth=a",
])
def test_real_model_http_cannot_escape_loopback(endpoint):
    with pytest.raises(ZombiePolicyRejected):
        tool._loopback(endpoint)


def test_previous_origins_cannot_be_fabricated_from_random_fixture():
    with pytest.raises(ZombiePolicyRejected, match="SHA"):
        tool.source_summaries(
            z1b_raw=b"synthetic", z2a_raw=b"synthetic",
        )


def test_one_http_journals_raw_before_policy_and_never_runs_world(tmp_path, monkeypatch):
    previous_a = tmp_path / "first.raw"
    previous_b = tmp_path / "second.raw"
    previous_a.write_bytes(b"unused-prior-A")
    previous_b.write_bytes(b"unused-prior-B")
    monkeypatch.setattr(tool, "source_summaries", lambda **kw: priors())
    monkeypatch.setenv("L_ZOMBIE_Z2B_REAL_GEMMA_DEV", "1")
    calls = []
    class FakeReply(io.BytesIO):
        pass
    def fake_call(req, timeout):
        calls.append((req, timeout))
        return FakeReply(payload())
    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_call)
    root = tmp_path / "new-real-http-evidence"
    r = tool.prepare_one_http(
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="Gemma-real-model-alias",
        z1b_original=previous_a, z2a_original=previous_b,
        evidence_root=root,
    )
    assert r["status"] == "PREPARED_POLICY_CONTRACT_PASS_NOT_PHYSICALLY_QUALIFIED"
    assert r["actual_gguf_sha_and_process_mapping_attested_here"] is False
    assert len(calls) == 1
    assert (root/"llama-response-1.raw.json").read_bytes() == payload()
    assert (root/"prepared-zombie-l2-policy-v1.json").exists()
    assert not (tmp_path/"world").exists()
    assert tool.prepare_one_http if root.exists() else False
    with pytest.raises(ZombiePolicyRejected):
        tool.prepare_one_http(
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="Gemma-real-model-alias", z1b_original=previous_a,
            z2a_original=previous_b, evidence_root=root,
        )
