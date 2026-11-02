"""S2-D strict JSON Schema + original S60-B1 compatibility, FAKE HTTP only."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.s57_owned_llama_backend import OwnedBackendSpec
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
    structured_review_format,
)
from adapters.mineflayer.s537_s2b_gated_l2_shadow import S2BGatedL2Shadow
from test_s537_s2b_gated_l2_shadow import _input, _read
from tools.s537_s2d_model_preflight import (
    S2DPreflightRejected,
    verify_owned_argv,
)


def _envelope(content, *, finish="stop", reasoning=None):
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return json.dumps({
        "model": "fake-s2d",
        "choices": [{
            "index": 0, "message": message, "finish_reason": finish,
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22},
    }).encode()


def _config(*, structured=True):
    return LoopbackTransportConfig(
        "fake-s2d", 19837, slots=1, max_tokens=64,
        connect_s=.25, read_s=.5, whole_s=.5,
        structured_json=structured,
    )


def test_strict_json_request_schema_in_original_s60_and_parent_compatibility():
    async def go():
        cfg = _config()
        shadow = S2BGatedL2Shadow(enabled=True, config=cfg, timeout_s=.5)
        source = _input()
        shadow.observe(source, owner_read=_read(source))
        req = shadow._request
        assert req is not None
        payload = json.loads(shadow._adapter._payload(req))
        assert set(payload) == {
            "model", "messages", "temperature", "max_tokens", "stream",
            "response_format",
        }
        assert payload["response_format"] == structured_review_format()
        assert payload["messages"][1]["role"] == "user"
        original = json.loads(payload["messages"][1]["content"])
        assert original["current_wb_l1_and_previous_s16"]["preceding_action_id"]
        assert original["original_owner"]["intent_event_generation"] == 1
        assert original["original_owner"]["retained_revision"] == 1
        await shadow.close()
        plain = S2BGatedL2Shadow(
            enabled=True, config=_config(structured=False), timeout_s=.5,
        )
        plain.observe(source, owner_read=_read(source))
        payload_plain = json.loads(plain._adapter._payload(plain._request))
        assert set(payload_plain) == {
            "model", "messages", "temperature", "max_tokens", "stream",
        }
        await plain.close()
    asyncio.run(go())


@pytest.mark.parametrize("fault", [
    "extra_field", "missing_field", "unknown_status", "empty_observation",
    "overlong_uncertainty", "duplicate_field", "reasoning_present",
    "truncated", "think_tag", "nonjson",
])
def test_strict_s60_response_rejects_unqualified_content(fault):
    async def go():
        adapter = LoopbackDisplacementAdapter(_config(), lambda _req: {})
        item = {
            "status": "ADVISORY", "observation": "prior movement ended",
            "uncertainty": "next zombie movement unknown",
        }
        if fault == "extra_field":
            item["command"] = "attack"
        elif fault == "missing_field":
            del item["uncertainty"]
        elif fault == "unknown_status":
            item["status"] = "ACTION"
        elif fault == "empty_observation":
            item["observation"] = ""
        elif fault == "overlong_uncertainty":
            item["uncertainty"] = "x" * 321
        elif fault == "duplicate_field":
            value = ('{"status":"ADVISORY","status":"DEFER",'
                     '"observation":"x","uncertainty":"x"}')
        elif fault == "think_tag":
            item["observation"] = "<think>bad"
        if fault != "duplicate_field":
            value = json.dumps(item)
        if fault == "nonjson":
            value = "I should move"
        with pytest.raises(TransportUnconfirmed):
            adapter._validate_response(
                _envelope(
                    value, finish="length" if fault == "truncated" else "stop",
                    reasoning="hidden thoughts" if fault == "reasoning_present"
                    else None,
                ),
                64,
            )
        assert adapter._validate_response(
            _envelope(json.dumps({
                "status": "DEFER", "observation": "source recorded",
                "uncertainty": "model not validated",
            })),
            64,
        ).startswith('{"observation":')
        plain = LoopbackDisplacementAdapter(
            _config(structured=False), lambda _req: {},
        )
        assert plain._validate_response(_envelope("Plain advisory"), 64) == (
            "Plain advisory"
        )
    asyncio.run(go())


def _spec(tmp_path: Path):
    executable = tmp_path / "llama-server"
    executable.write_bytes(b"fake binary")
    executable.chmod(0o755)
    model = tmp_path / "test.gguf"
    model.write_bytes(b"not-real-gguf")
    spec = OwnedBackendSpec(
        binary=executable, gguf=model, binary_sha256="a" * 64,
        gguf_sha256="b" * 64, alias="gemma4-test", port=19837,
        gpu_layers=99, ctx_size=8192, inference_parallel=1,
    )
    argv = (
        str(executable), "--model", str(model), "--alias", "gemma4-test",
        "--host", "127.0.0.1", "--port", "19837",
        "--ctx-size", "8192", "--parallel", "1",
        "--n-gpu-layers", "99", "--reasoning", "off",
    )
    return spec, argv


def test_running_model_argv_explicit_reasoning_off(tmp_path):
    spec, argv = _spec(tmp_path)
    verify_owned_argv(
        argv, spec, running_exe=spec.binary, same_user=True,
    )


@pytest.mark.parametrize("fault", [
    "not_off", "format_only", "wrong_gguf", "wrong_port",
    "wrong_alias", "wrong_ctx", "wrong_slot", "duplicate_reasoning",
    "wrong_gpu", "foreign_uid", "foreign_exe",
])
def test_reasoning_off_and_original_binary_source_require_exact_args(
    tmp_path, fault,
):
    spec, argv = _spec(tmp_path)
    argv = list(argv)
    exe = spec.binary
    uid = True
    def set_after(flag, value):
        argv[argv.index(flag) + 1] = value
    if fault == "not_off":
        set_after("--reasoning", "auto")
    elif fault == "format_only":
        argv[-2:] = ["--reasoning-format", "none"]
    elif fault == "wrong_gguf":
        set_after("--model", "/fake/model.gguf")
    elif fault == "wrong_port":
        set_after("--port", "19838")
    elif fault == "wrong_alias":
        set_after("--alias", "foreign")
    elif fault == "wrong_ctx":
        set_after("--ctx-size", "4096")
    elif fault == "wrong_slot":
        set_after("--parallel", "2")
    elif fault == "duplicate_reasoning":
        argv += ["--reasoning", "off"]
    elif fault == "wrong_gpu":
        set_after("--n-gpu-layers", "0")
    elif fault == "foreign_uid":
        uid = False
    elif fault == "foreign_exe":
        exe = spec.gguf
    with pytest.raises(S2DPreflightRejected):
        verify_owned_argv(tuple(argv), spec, running_exe=exe, same_user=uid)
