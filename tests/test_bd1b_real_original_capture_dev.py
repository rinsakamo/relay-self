"""One-shot owned raw-model capture with CPU-only HTTP/Paper fixtures.

The mocked urllib response is NOT real Gemma, despite raw HTTP fixture files.
"""
import asyncio
import json
from pathlib import Path

import pytest

import relay_self.bd1b_real_issuer_preflight_dev as preflight
from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from experiments.bd1b_real_original_capture_dev import capture_bd1b_real_original_once
from experiments.stage24g_model_gate_dev import Stage24gModelGateReceipt
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    LlamaSlotIdleReceipt,
)
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


_REAL_CALL = LlamaCppRelayProvider.__call__


def _args(case, evidence_dir):
    return dict(
        bridge=case[1], boot=case[2], world=case[3], links=case[4],
        self_id="A", gguf_path=Path("/models/pin.gguf"), llama_pid=32145,
        model_alias="model", llama_endpoint="http://127.0.0.1:8080",
        evidence_dir=evidence_dir,
    )


def _wire(monkeypatch, choice):
    # Restore the genuine codec path after the synthetic setup's provider patch.
    from experiments.bd1b_real_original_capture_dev import BD1bSinglePostRawProvider

    monkeypatch.setattr(BD1bSinglePostRawProvider, "__call__", _REAL_CALL)
    monkeypatch.setattr(LlamaCppSingleSlotWitness, "require_idle",
                        lambda self: LlamaSlotIdleReceipt(
                            self.backend_ref, 0, 1, False, "synthetic-idle",
                        ))
    monkeypatch.setattr(preflight, "verify_stage24g_model_gate", lambda **kw:
                        Stage24gModelGateReceipt(
                            32145, "model", "/models/pin.gguf", "a" * 64,
                            "RTX 3060", "b" * 64, "c" * 64, 0, 1, "d" * 64,
                        ))
    from experiments import stage28c2c_real_original_l1_dev as raw_module

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, max_bytes=None):
            payload = {"choices": [{"message": {"content": json.dumps({
                "status": "resolved", "choice_id": choice,
            })}, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 8, "completion_tokens": 4,
                                 "total_tokens": 12}}
            return json.dumps(payload).encode()

    monkeypatch.setattr(raw_module.urllib.request, "urlopen",
                        lambda request, timeout: FakeResponse())


@pytest.mark.parametrize("choice,expected", [("1", "ADOPT"), ("2", "HOLD"), ("3", "DECLINE")])
def test_original_raw_http_one_post_and_memory_boundary(tmp_path, monkeypatch,
                                                        choice, expected):
    case = _configured(tmp_path / "self", monkeypatch, need=True)
    bridge = case[1]
    before = _files(bridge)
    _wire(monkeypatch, choice)
    root = tmp_path / "capture"
    try:
        output = asyncio.run(capture_bd1b_real_original_once(**_args(case, root)))
        info = json.loads(output.read_bytes())
        assert info["classification"] == "BD1B_REAL_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        assert info["selection"] == expected
        assert info["raw_http"]["http_status"] == 200
        assert set(x.name for x in (root / "http").iterdir()) == {
            "bounded-1-request-body.bin", "bounded-1-response-body.bin",
            "bounded-1-http-evidence.json",
        }
        assert not info["physical_action_issued"]
        assert not info["real_model_independently_audited"]
        assert (root / "physical.before.wal").read_bytes() == (
            root / "physical.after.wal"
        ).read_bytes()
        if expected == "ADOPT":
            assert (root / "cognition.after.json").read_bytes() != (
                root / "cognition.before.json"
            ).read_bytes()
            assert len(bridge.owners["A"].retained.exploration_continuity.questions) == 1
        else:
            assert _files(bridge) == before
            assert (root / "cognition.after.json").read_bytes() == (
                root / "cognition.before.json"
            ).read_bytes()
    finally:
        if bridge.inference_lane:
            bridge.inference_lane._pool.shutdown(wait=True)


def test_uncertified_restored_schema_refuses_before_evidence_or_post(tmp_path, monkeypatch):
    case = _configured(tmp_path / "self", monkeypatch, need=True)
    case[1].cognitive_work._present_schemas.clear()
    _wire(monkeypatch, "1")
    root = tmp_path / "capture"
    with pytest.raises(preflight.BD1bRealIssuerHold,
                       match="RESTORED_SCHEMA_ACTIVATION_NOT_ATTESTED"):
        asyncio.run(capture_bd1b_real_original_once(**_args(case, root)))
    assert not root.exists()
    assert case[1].inference_lane is None


def test_evidence_replay_refused_before_model(tmp_path, monkeypatch):
    case = _configured(tmp_path / "self", monkeypatch, need=True)
    root = tmp_path / "capture"
    root.mkdir()
    with pytest.raises(preflight.BD1bRealIssuerHold):
        asyncio.run(capture_bd1b_real_original_once(**_args(case, root)))
    assert case[1].inference_lane is None


def test_invalid_choice_does_not_write_question(tmp_path, monkeypatch):
    case = _configured(tmp_path / "self", monkeypatch, need=True)
    bridge = case[1]
    before = _files(bridge)
    _wire(monkeypatch, "99")
    try:
        root = tmp_path / "capture"
        output = asyncio.run(capture_bd1b_real_original_once(**_args(case, root)))
        info = json.loads(output.read_bytes())
        assert info["selection"] == "UNRESOLVED"
        assert _files(bridge) == before
    finally:
        if bridge.inference_lane:
            bridge.inference_lane._pool.shutdown(wait=True)


def test_model_http_failure_leaves_hold_and_fences_real_owner(tmp_path, monkeypatch):
    case = _configured(tmp_path / "self", monkeypatch, need=True)
    _wire(monkeypatch, "1")
    from experiments import stage28c2c_real_original_l1_dev as raw_module

    def no_http(*args, **kwargs):
        raise TimeoutError("synthetic network timeout")

    monkeypatch.setattr(raw_module.urllib.request, "urlopen", no_http)
    root = tmp_path / "capture"
    before = _files(case[1])
    try:
        with pytest.raises(Exception):
            asyncio.run(capture_bd1b_real_original_once(**_args(case, root)))
        hold = json.loads((root / "issuer-HOLD.json").read_bytes())
        assert hold["classification"] == "BD1B_REAL_HOLD"
        assert hold["model_post_attempted"] == 1
        assert _files(case[1]) == before
        assert case[1].cognitive_work.quarantined_scope("A")
    finally:
        if case[1].inference_lane:
            case[1].inference_lane._pool.shutdown(wait=True)
