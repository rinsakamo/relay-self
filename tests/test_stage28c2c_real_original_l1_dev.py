"""Stage28c2c: raw one-shot Gemma HTTP evidence and no-World CLI guards.

All mock network/owner sources synthetic. Never claim real model/Paper here.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from adapters.llama_cpp.relay_engine import (
    render_llama_cpp_request,
)
from experiments import stage28c2c_independent_real_l1_audit_dev as audit
from experiments import stage28c2c_real_original_l1_dev as runner
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import (
    validate_fresh_original_l1_result,
)
from test_stage28c2c_fresh_recovered_l1_dev import _fake_l1, _prepare, _ready


class _FakeHTTP:
    status = 200

    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, _size):
        return self.content


def _provider(tmp_path, monkeypatch, *, choice="1", status=200):
    root = tmp_path / "raw"
    root.mkdir()
    response = {
        "choices": [{
            "message": {
                "content": json.dumps(
                    {"status": "resolved", "choice_id": choice},
                    sort_keys=True, separators=(",", ":"),
                ),
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 27, "completion_tokens": 8, "total_tokens": 35,
        },
    }
    content = json.dumps(response, sort_keys=True).encode()
    captured = []

    def fake_urlopen(request, timeout):
        assert request.method == "POST"
        assert timeout == 10
        assert request.full_url == "http://127.0.0.1:9090/v1/chat/completions"
        assert request.data
        captured.append(request.data)
        fake = _FakeHTTP(content)
        fake.status = status
        return fake

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    provider = runner.OriginalRawBoundedLlamaProvider(
        endpoint="http://127.0.0.1:9090/v1/chat/completions",
        model="gemma-offline-test", raw_dir=root, timeout=10,
    )
    return provider, captured, response, root


def test_stage28c2c_raw_http_original_bytes_exact_once(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    provider, captured, _, root = _provider(tmp_path, monkeypatch)
    model = provider(turn.request, mode=CognitionMode.BOUNDED)
    assert isinstance(model, ProviderDecision)
    assert model.choice_id == "1"
    assert model.call_facts.prompt_tokens == 27
    assert model.call_facts.completion_tokens == 8
    assert provider.attempted == 1
    assert provider.completed == 1
    assert len(captured) == 1
    raw = (root / "bounded-1-request-body.bin").read_bytes()
    assert raw == captured[0]
    expected = json.dumps(render_llama_cpp_request(
        turn.request, mode=CognitionMode.BOUNDED, model=provider.model,
    ), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert raw == expected
    proof = json.loads((root / "bounded-1-http-evidence.json").read_text())
    assert proof["request_body_sha256"] == hashlib.sha256(raw).hexdigest()
    assert proof["response_body_sha256"] == hashlib.sha256(
        (root / "bounded-1-response-body.bin").read_bytes()
    ).hexdigest()
    assert proof["http_status"] == 200


def test_stage28c2c_two_actual_requests_then_third_refused(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    provider, captured, _, root = _provider(tmp_path, monkeypatch)
    assert provider(turn.request, mode=CognitionMode.BOUNDED).choice_id == "1"
    assert provider(turn.request, mode=CognitionMode.BOUNDED).choice_id == "1"
    with pytest.raises(runner.Stage28c2cRealL1Hold):
        provider(turn.request, mode=CognitionMode.BOUNDED)
    assert len(captured) == 2
    assert provider.attempted == provider.completed == 2
    assert not (root / "bounded-3-request-body.bin").exists()


@pytest.mark.parametrize("tamper", ["wrong-choice", "wrong-prompt", "wrong-reply",
                                    "wrong-source-hash", "wrong-probe",
                                    "wrong-status", "changed-owner-epoch"])
def test_stage28c2c_independent_model_audit_rejects_forgery(
    tmp_path, monkeypatch, tamper,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    provider, _, _, raw = _provider(tmp_path, monkeypatch)
    _ = provider(turn.request, mode=CognitionMode.BOUNDED)
    lane, token = _fake_l1(case, turn, choice="1")
    result = validate_fresh_original_l1_result(
        bridge=case[1], boot=case[2], turn=turn,
        lane=lane, ticket=token,
    )
    result = replace(
        result, backend_ref="stage28c2c-pid-9001",
        prompt_tokens=27, completion_tokens=8,
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir(exist_ok=True)  # original _ready fixture owns this root
    dest = evidence / "stage28c2c-llama-original"
    raw.rename(dest)
    report = {
        "native_login_evidence": {
            sid: asdict(case[1].last_login_evidence[sid])
            for sid in ("A", "B")
        },
        "stage28c2c_original_turns": {"A": {
            "self_id": turn.self_id,
            "owner_scope": list(turn.owner_scope),
            "native_probe_ref": turn.native_probe_ref,
            "native_probe_seq": turn.native_probe_seq,
            "pattern_registry_revision": turn.pattern_registry_revision,
            "candidate_set_sha256": turn.candidate_set_sha256,
            "paper_session_id": turn.paper_session_id,
            "paper_boot_id": turn.paper_boot_id,
            "allowed_skills": [], "presets": [],
            "original_owner_adopted": True,
            "old_l1_result_reused": False,
            "physical_action_issue_authorized": False,
            "request": asdict(turn.request),
        }},
        "stage28c2c_l1_results": {"A": asdict(result)},
        "stage28c2c_model_raw_sha256": {
            x.name: runner.file_sha256(x) for x in dest.iterdir()
        },
    }
    gate = {"model_alias": "gemma-offline-test", "llama_pid": 9001}
    if tamper == "wrong-choice":
        report["stage28c2c_l1_results"]["A"]["choice_id"] = "2"
    elif tamper == "wrong-prompt":
        report["stage28c2c_original_turns"]["A"]["request"]["choices"][0][
            "description"] = "MOVE"
    elif tamper == "wrong-reply":
        (dest / "bounded-1-response-body.bin").write_text("{}")
    elif tamper == "wrong-source-hash":
        report["stage28c2c_model_raw_sha256"]["bounded-1-request-body.bin"] = "0" * 64
    elif tamper == "wrong-probe":
        report["native_login_evidence"]["A"]["observation_ref"] = "old"
    elif tamper == "wrong-status":
        report["stage28c2c_l1_results"]["A"]["model_status"] = "unresolved"
    elif tamper == "changed-owner-epoch":
        report["stage28c2c_original_turns"]["A"]["owner_scope"][0] += 1
    monkeypatch.setattr(
        audit, "_native_source", lambda *_args, **_kwargs: turn.original_probe,
    )
    if tamper == "wrong-reply":
        # A locally copied response changed, but its *expected* SHA didn't.
        assert runner.file_sha256(dest / "bounded-1-response-body.bin") != (
            report["stage28c2c_model_raw_sha256"]["bounded-1-response-body.bin"]
        )
    with pytest.raises(audit.Stage28c2cAuditHold):
        audit._validate_model_original_one(
            evidence=evidence, sid="A", ordinal=1,
            report=report, original_owner=case[1].owners["A"],
            boot=case[2], gate=gate,
        )


def test_stage28c2c_independent_original_model_synthetic_ok(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    provider, _, _, raw = _provider(tmp_path, monkeypatch)
    provider(turn.request, mode=CognitionMode.BOUNDED)
    lane, token = _fake_l1(case, turn, choice="1")
    result = replace(
        validate_fresh_original_l1_result(
            bridge=case[1], boot=case[2], turn=turn,
            lane=lane, ticket=token,
        ),
        backend_ref="stage28c2c-pid-9001",
        prompt_tokens=27, completion_tokens=8,
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir(exist_ok=True)  # original _ready fixture owns this root
    dest = evidence / "stage28c2c-llama-original"
    raw.rename(dest)
    report = {
        "native_login_evidence": {
            sid: asdict(case[1].last_login_evidence[sid])
            for sid in ("A", "B")
        },
        "stage28c2c_original_turns": {"A": {
            "self_id": turn.self_id,
            "owner_scope": list(turn.owner_scope),
            "native_probe_ref": turn.native_probe_ref,
            "native_probe_seq": turn.native_probe_seq,
            "pattern_registry_revision": turn.pattern_registry_revision,
            "candidate_set_sha256": turn.candidate_set_sha256,
            "paper_session_id": turn.paper_session_id,
            "paper_boot_id": turn.paper_boot_id,
            "allowed_skills": [], "presets": [],
            "original_owner_adopted": True,
            "old_l1_result_reused": False,
            "physical_action_issue_authorized": False,
            "request": asdict(turn.request),
        }},
        "stage28c2c_l1_results": {"A": asdict(result)},
        "stage28c2c_model_raw_sha256": {
            x.name: runner.file_sha256(x) for x in dest.iterdir()
        },
    }
    monkeypatch.setattr(audit, "_native_source", lambda *_a, **_k: turn.original_probe)
    verified = audit._validate_model_original_one(
        evidence=evidence, sid="A", ordinal=1,
        report=report, original_owner=case[1].owners["A"],
        boot=case[2], gate={"model_alias": "gemma-offline-test", "llama_pid": 9001},
    )
    assert verified["model_choice_id"] == "1"
    assert verified["physical_action_issued"] is False


def _cli(tmp_path, *extra):
    return [
        "stage28c2c", "--generation", str(tmp_path / "generation"),
        "--restored", str(tmp_path / "restored"),
        "--stage28b-evidence", str(tmp_path / "source"),
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--plugin-jar", str(tmp_path / "plugin.jar"),
        "--gguf", str(tmp_path / "gemma.gguf"),
        "--llama-pid", "9001", "--model-alias", "gemma-test",
        "--llama-endpoint", "http://127.0.0.1:9090/v1/chat/completions",
        "--eula-accepted", *extra,
    ]


def test_stage28c2c_inspect_only_never_starts_world_or_posts_model(
    tmp_path, monkeypatch, capsys,
):
    gate = SimpleNamespace(
        llama_pid=9001, gpu_name="NVIDIA RTX 3060",
        slot_count=1, slot_id=0,
    )
    monkeypatch.setattr(runner, "inspect_real_l1_sources", lambda **_kw: gate)
    async def never_execute(**_kw):
        pytest.fail("inspection unexpectedly created Paper or sent real Gemma")
    monkeypatch.setattr(runner, "run_real_original_a_b_l1", never_execute)
    monkeypatch.setattr(sys, "argv", _cli(tmp_path, "--inspect-only"))
    assert runner.main() == 0
    assert "world_started=false model_post=false" in capsys.readouterr().out


@pytest.mark.parametrize("flags", [
    ("--execute-once",), ("--execute-once", "--real-world-dev-grant"),
    ("--execute-once", "--model-post-grant"),
    ("--inspect-only", "--model-post-grant"),
])
def test_stage28c2c_cannot_run_without_both_explicit_grants(
    tmp_path, monkeypatch, flags,
):
    monkeypatch.setattr(sys, "argv", _cli(tmp_path, *flags))
    monkeypatch.setattr(
        runner, "inspect_real_l1_sources",
        lambda **_kw: pytest.fail("missing grant reached preflight"),
    )
    assert runner.main() == 2


def test_stage28c2c_runner_passes_exact_post_worldbody_callback_only(
    tmp_path, monkeypatch,
):
    gate = runner.Stage24gModelGateReceipt(
        9001, "gemma-test", "gemma.gguf", "0"*64,
        "NVIDIA RTX 3060", "a"*64, "b"*64, 0, 1, "c"*64,
    )
    async def fake_owned(**kwargs):
        assert callable(kwargs["on_reconnected"])
        assert kwargs["on_reconnected"].__name__ == "on_reconnected"
        return tmp_path / "synthetic-only-not-actual-world.json"
    monkeypatch.setattr(runner, "run_restored_a_b_real_observation", fake_owned)
    result = asyncio.run(runner.run_real_original_a_b_l1(
        generation=tmp_path / "gen", restored=tmp_path / "restored",
        stage28b_evidence=tmp_path / "stage28b",
        paper_jar=tmp_path / "paper.jar", plugin_jar=tmp_path / "plugin.jar",
        execution_dir=tmp_path / "new-exec", evidence_dir=tmp_path / "new-evidence",
        java="java", node="node",
        llama_endpoint="http://127.0.0.1:9090/v1/chat/completions",
        model_alias="gemma-test", gate=gate,
    ))
    assert "synthetic-only" in result.name
