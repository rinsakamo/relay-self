"""I2e original two HTTP entity bodies and independent CPU auditor regression.

No real GGUF, HTTP socket or Minecraft: urllib is monkeypatched. The runner
still uses the actual original resident L2/L1 Ticket and Owner interfaces.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from experiments import i_lane_i2e_original_dual_model_raw_dev as capture
from experiments.i_lane_i2e_independent_dual_model_audit_dev import (
    I2eIndependentAuditHold,
    independently_audit_i2e_model_bundle,
)
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.relay_engine import CognitionMode
from test_i_lane_i2_original_exploration_handoff_dev import _args
from test_i_lane_i2b_original_shared_l1_dev import _fixture


class _HTTP:
    status = 200

    def __init__(self, body, status=200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, _maximum):
        return self.body


def _pattern_json():
    return json.dumps({
        "pattern_id": "learned-i2e", "version": 1,
        "schema_id": "exploration", "kind": "GOAL",
        "predicate": "EXPLORE", "goal_id": "EXPLORE_WORLD",
        "skill_id": None, "skill_version": None, "target_kind": None,
    }, sort_keys=True, separators=(",", ":"))


def _environment(tmp_path, monkeypatch, *, vote="1", bad_model=False,
                 http_status=200):
    case, lane = _fixture(tmp_path, monkeypatch, exploration=False)
    bridge = case[1]
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        owner.retained = replace(
            owner.retained, pattern_registry=owner.pattern_registry,
        )
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    directory = tmp_path / "original-raw"
    directory.mkdir()
    provider = capture.I2eOriginalDualModeRawProvider(
        endpoint="http://127.0.0.1:18999/v1/chat/completions",
        model="cpu-fixture-not-real-gguf", raw_dir=directory, timeout=4,
    )
    lane.provider = provider
    bridge.inference_lane = lane
    posted = []

    def urlopen(request, timeout):
        assert request.method == "POST"
        assert timeout == 4
        assert request.full_url == provider.endpoint
        body = json.loads(request.data)
        posted.append(body)
        content = (
            "NOT JSON" if bad_model else _pattern_json()
        ) if len(posted) == 1 else (
            json.dumps({"status": "resolved", "choice_id": vote})
            if vote is not None else
            json.dumps({"status": "unresolved", "choice_id": None})
        )
        response = {
            "choices": [{
                "message": {"content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 13,
                "total_tokens": 38,
            },
        }
        return _HTTP(
            json.dumps(response, sort_keys=True).encode("utf-8"),
            status=http_status,
        )

    monkeypatch.setattr(capture.urllib.request, "urlopen", urlopen)
    return case, lane, provider, posted, directory


def _run(case, lane, provider):
    return asyncio.run(capture.run_i2e_original_dual_raw(
        **_args(case, "A"), lane=lane, provider=provider, timeout_s=3,
    ))


@pytest.mark.parametrize(("vote", "outcome"), [
    ("1", "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA"),
    ("2", "DEFER"), (None, "UNRESOLVED"),
])
def test_i2e_real_lane_methods_and_independent_raw_bundle_cpu(
    tmp_path, monkeypatch, vote, outcome,
):
    case, lane, provider, posted, directory = _environment(
        tmp_path, monkeypatch, vote=vote,
    )
    try:
        before_b = case[1].owners["B"].retained
        receipt = _run(case, lane, provider)
        assert len(posted) == 2
        assert provider.attempted == provider.completed == 2
        assert "response_format" not in posted[0]
        assert posted[1]["response_format"]["type"] == "json_schema"
        assert receipt["outcome"]["outcome"] == outcome
        assert receipt["world_independent_audit_attested"] is False
        assert receipt["all_physical_actions"] == 0
        audited = independently_audit_i2e_model_bundle(directory)
        assert audited["classification"] == "I2E_DUAL_RAW_MODEL_AND_OWNER_CPU_BUNDLE_AUDITED"
        assert audited["model_result"] == outcome
        assert audited["l2"]["prompt_tokens"] == 25
        assert audited["l1"]["completion_tokens"] == 13
        assert audited["original_native_paper_world_independently_verified"] is False
        assert audited["real_world_dev_pass"] is False
        assert audited["physical_action_count"] == 0
        assert case[1].owners["B"].retained is before_b
        with pytest.raises(capture.I2eRawModelHold):
            _run(case, lane, provider)
        assert provider.attempted == 2
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("fault", [
    "open-request", "open-response", "bounded-request", "bounded-response",
    "first-http-sha", "second-http-sha", "missing-file", "extra-file",
    "before-owner", "after-owner", "tamper-choice", "foreign-self",
    "foreign-ticket", "fake-World-pass", "altered-l2-proposal",
    "changed-model", "wrong-open-request-id", "wrong-owner-outcome",
])
def test_i2e_independent_raw_rejects_forged_or_replayed_evidence(
    tmp_path, monkeypatch, fault,
):
    case, lane, provider, posted, directory = _environment(
        tmp_path, monkeypatch,
    )
    try:
        _run(case, lane, provider)
        report_path = directory / "i2e-dual-model-report.json"
        report = json.loads(report_path.read_bytes())
        if fault in ("open-request", "open-response",
                     "bounded-request", "bounded-response"):
            path = directory / ({
                "open-request": "open-l2-request-body.bin",
                "open-response": "open-l2-response-body.bin",
                "bounded-request": "bounded-l1-request-body.bin",
                "bounded-response": "bounded-l1-response-body.bin",
            }[fault])
            with path.open("ab") as stream:
                stream.write(b"FORGED")
        elif fault in ("first-http-sha", "second-http-sha"):
            label = "open-l2" if fault == "first-http-sha" else "bounded-l1"
            path = directory / (label + "-http-evidence.json")
            row = json.loads(path.read_bytes())
            row["response_body_sha256"] = "0" * 64
            path.write_text(json.dumps(row))
        elif fault == "missing-file":
            (directory / "bounded-l1-response-body.bin").unlink()
        elif fault == "extra-file":
            (directory / "third-post.bin").write_bytes(b"not permitted")
        elif fault in ("before-owner", "after-owner"):
            path = directory / (
                "before-cognition.json" if fault == "before-owner"
                else "after-cognition.json"
            )
            path.write_bytes(b"FORGED")
        elif fault == "tamper-choice":
            report["bounded_l1_request"]["choices"][0]["description"] = "MOVE"
        elif fault == "foreign-self":
            report["self_id"] = "B"
        elif fault == "foreign-ticket":
            report["open_l2_ticket"]["native_session_id"] = "foreign-native"
        elif fault == "fake-World-pass":
            report["world_independent_audit_attested"] = True
        elif fault == "altered-l2-proposal":
            report["l2_pattern"]["pattern_id"] = "forged-by-auditor"
        elif fault == "changed-model":
            report["model_alias"] = "different-GGUF"
        elif fault == "wrong-open-request-id":
            report["open_l2_request"]["request_id"] = "i2d-l2:foreign"
        else:
            report["outcome"]["outcome"] = "DEFER"
        if fault in {
            "tamper-choice", "foreign-self", "foreign-ticket", "fake-World-pass",
            "altered-l2-proposal", "changed-model",
            "wrong-open-request-id", "wrong-owner-outcome",
        }:
            report_path.write_text(json.dumps(report))
        with pytest.raises(I2eIndependentAuditHold):
            independently_audit_i2e_model_bundle(directory)
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("failure", ["bad-l2", "http-not-200"])
def test_i2e_partial_model_failure_keeps_original_raw_holds_no_retry(
    tmp_path, monkeypatch, failure,
):
    case, lane, provider, posted, directory = _environment(
        tmp_path, monkeypatch,
        bad_model=(failure == "bad-l2"),
        http_status=503 if failure == "http-not-200" else 200,
    )
    try:
        with pytest.raises((capture.I2eRawModelHold, RuntimeError, ValueError)):
            _run(case, lane, provider)
        assert len(posted) == 1
        assert provider.attempted == 1
        assert (directory / "open-l2-request-body.bin").exists()
        assert not (directory / "i2e-dual-model-report.json").exists()
        with pytest.raises(I2eIndependentAuditHold):
            independently_audit_i2e_model_bundle(directory)
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)


def test_i2e_no_model_or_world_without_original_bridge_lane(
    tmp_path, monkeypatch,
):
    case, lane, provider, posted, directory = _environment(tmp_path, monkeypatch)
    try:
        case[1].inference_lane = None
        with pytest.raises(capture.I2eRawModelHold):
            _run(case, lane, provider)
        assert not posted
        assert not list(directory.iterdir())
    finally:
        lane._pool.shutdown(wait=True)
