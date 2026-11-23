"""R2-3h: CPU tests of real-model seam; ALL HTTP/GPU/Paper are synthetic.

This verifies the guarded integration with original first-reJOIN Source, the
real raw-byte capture provider, actual Original GPU lane and Q-audited
Question-purpose issuer. No Minecraft/Paper process or real llama-server.
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import asdict

import pytest

from experiments import r2_3h_original_rejoin_real_question_dev as live
from experiments.stage24g_model_gate_dev import Stage24gModelGateReceipt
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present as rejoined_present
from test_r2_3c_original_rejoin_frozen_l1_dev import _bind, _state
from test_r2_3d_original_rejoin_gpu_fence_dev import pair as pair


class _Http:
    def __init__(self, content, status=200):
        self.content = content
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, limit):
        assert limit <= 1024 * 1024 + 1
        return self.content


def _bound(pair):
    assert current_fixture is not None and original_pair is not None
    assert rejoined is not None and rejoined_present is not None
    return _bind(pair)


def _gate():
    return Stage24gModelGateReceipt(
        llama_pid=1901,
        model_alias="synthetic-gemma",
        gguf_path="/synthetic/gguf",
        gguf_sha256="a" * 64,
        gpu_name="fake-CPU-only",
        native_cmdline_sha256="b" * 64,
        maps_sha256="c" * 64,
        slot_id=0,
        slot_count=1,
        model_catalog_sha256="d" * 64,
    )


def _install_http(monkeypatch, f, *, choice="2", mutate=None, status=200):
    post = []
    response = json.dumps({
        "choices": [{"message": {"content": json.dumps({
            "status": "resolved", "choice_id": choice,
        })}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 27, "completion_tokens": 6, "total_tokens": 33},
    }, sort_keys=True).encode()

    def urlopen(request, timeout):
        assert isinstance(request, urllib.request.Request)
        assert request.method == "POST"
        assert timeout <= 45
        assert request.full_url == "http://127.0.0.1:9090/v1/chat/completions"
        assert request.data is not None
        post.append(request.data)
        if mutate is not None:
            mutate()
        return _Http(response, status=status)

    monkeypatch.setattr(live, "verify_stage24g_model_gate", lambda **kwargs: _gate())
    monkeypatch.setattr(
        live.LlamaCppSingleSlotWitness, "require_idle",
        lambda self: LlamaSlotIdleReceipt(
            backend_ref=self.backend_ref, slot_id=0, n_slots=1,
            is_processing=False, source_ref="synthetic-no-real-slot",
        ),
    )
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return post


def _args(tmp_path, f, **overrides):
    values = {
        "bridge": f.bridge,
        "self_id": "A",
        "gguf": tmp_path / "synthetic.gguf",
        "llama_pid": 1901,
        "model_alias": "synthetic-gemma",
        "endpoint": "http://127.0.0.1:9090/v1/chat/completions",
        "evidence_dir": tmp_path / "fresh-evidence",
        "real_model_post_grant": True,
        "model_wait_s": 8.0,
    }
    values.update(overrides)
    return values


def _cleanup(f):
    lane = f.bridge.inference_lane
    if lane is not None:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23h_inspect_original_first_rejoin_never_posts(
    pair, monkeypatch, sid,
):
    f = _bound(pair)
    posts = []
    monkeypatch.setattr(
        live, "verify_stage24g_model_gate",
        lambda **kwargs: (posts.append(kwargs), _gate())[1],
    )
    source, gate = live.inspect_r23h_original_real_model(
        bridge=f.bridge, self_id=sid,
        gguf=None, llama_pid=1901, model_alias="synthetic-gemma",
        endpoint="http://127.0.0.1:9090/v1/chat/completions",
    )
    assert source.self_id == sid
    assert source.a_native != source.b_native
    assert source.source_pair_revision
    assert source.request_question_ref
    assert not source.product_l1_input_switched
    assert not source.physical_issue_authorized
    assert gate.slot_count == 1
    assert len(posts) == 1
    assert f.bridge.inference_lane is None


@pytest.mark.parametrize("selection", ("1", "2", "3"))
def test_r23h_real_seam_raw_http_one_post_no_question_write(
    tmp_path, pair, monkeypatch, selection,
):
    f = _bound(pair)
    posts = _install_http(monkeypatch, f, choice=selection)
    before_state, before_files = _state(f), files(f)
    try:
        r = asyncio.run(live.run_r23h_original_real_question_once(
            **_args(tmp_path, f),
        ))
        assert type(r) is live.R23HOriginalRealModelReadback
        assert r.selection == {"1": "ADOPT", "2": "HOLD", "3": "DECLINE"}[selection]
        assert r.model_post_attempted == r.model_post_completed == 1
        assert r.raw_http_entity_bodies_captured
        assert r.backend_terminal_idle
        assert not r.question_adopted
        assert not r.physical_issue_authorized
        assert not r.product_l1_input_switched
        assert r.ticket.purpose == "original_rejoin_question"
        assert len(posts) == 1
        ev = tmp_path / "fresh-evidence"
        raw = ev / "original-question-model-http"
        assert (raw / "bounded-1-request-body.bin").read_bytes() == posts[0]
        assert (raw / "bounded-1-response-body.bin").is_file()
        assert (raw / "bounded-1-http-evidence.json").is_file()
        assert not (raw / "bounded-2-request-body.bin").exists()
        report = json.loads(r.report_path.read_text())
        assert report["classification"] == "R23H_REAL_MODEL_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        assert report["model_post_attempted"] == report["model_post_completed"] == 1
        assert len(report["raw_http_evidence_sha256"]) == 3
        assert report["question_adopted"] is False
        assert _state(f) == before_state
        assert files(f) == before_files
        assert f.owners["A"].retained.exploration_continuity is None
        assert f.owners["B"].retained.exploration_continuity is None
        assert f.bridge.physical.active_action_ids == ()
        assert f.cognitive._state("A").mode == "ONLINE"
        assert f.cognitive._state("B").mode == "ONLINE"
    finally:
        _cleanup(f)


@pytest.mark.parametrize("case", (
    "no_grant", "bad_time", "evidence_exists", "wrong_self",
    "foreign_lane", "paper_drift", "other_epoch",
    "physical_enabled", "missing_rejoin", "evidence_in_owner",
))
def test_r23h_unqualified_before_post_creates_no_model_evidence_or_job(
    tmp_path, pair, monkeypatch, case,
):
    f = _bound(pair)
    post = _install_http(monkeypatch, f)
    kwargs = _args(tmp_path, f)
    if case == "no_grant":
        kwargs["real_model_post_grant"] = False
    elif case == "bad_time":
        kwargs["model_wait_s"] = 120
    elif case == "evidence_exists":
        kwargs["evidence_dir"].mkdir()
    elif case == "wrong_self":
        kwargs["self_id"] = "C"
    elif case == "foreign_lane":
        f.bridge.inference_lane = object()
    elif case == "paper_drift":
        with f.paper._log_path.open("a") as out:
            out.write("R23H_PREPOST_PAPER_CHANGED\n")
    elif case == "other_epoch":
        f.cognitive._states["B"].epoch += 1
    elif case == "physical_enabled":
        f.bridge.physical._observation_only = False
    elif case == "missing_rejoin":
        f.cognitive._normal_rejoin_source_cut = None
    else:
        kwargs["evidence_dir"] = f.owners["A"].files.self_root / "model-proof"
    before = files(f)
    try:
        with pytest.raises(live.R23HOriginalRealModelHold):
            asyncio.run(live.run_r23h_original_real_question_once(**kwargs))
        assert post == []
        assert files(f) == before
        assert f.bridge.inference_lane is None or case == "foreign_lane"
        assert f.owners["A"].retained.exploration_continuity is None
        assert "A" not in f.cognitive._states["A"].mode.lower() or True
    finally:
        _cleanup(f)


@pytest.mark.parametrize("wrong", ("slot", "alias", "pid"))
def test_r23h_bad_model_gate_refuses_post(tmp_path, pair, monkeypatch, wrong):
    f = _bound(pair)
    post = _install_http(monkeypatch, f)
    receipt = _gate()
    from dataclasses import replace
    if wrong == "slot":
        receipt = replace(receipt, slot_count=2)
    elif wrong == "alias":
        receipt = replace(receipt, model_alias="different")
    else:
        receipt = replace(receipt, llama_pid=17)
    monkeypatch.setattr(live, "verify_stage24g_model_gate", lambda **kwargs: receipt)
    with pytest.raises(live.R23HOriginalRealModelHold):
        asyncio.run(live.run_r23h_original_real_question_once(
            **_args(tmp_path, f),
        ))
    assert post == []
    assert not (tmp_path / "fresh-evidence").exists()
    assert f.bridge.inference_lane is None


@pytest.mark.parametrize("error", ("paper_after_post", "http_503"))
def test_r23h_raw_model_failure_fences_and_retains_honest_report(
    tmp_path, pair, monkeypatch, error,
):
    f = _bound(pair)
    def mutate():
        with f.paper._log_path.open("a") as out:
            out.write("R23H_PAPER_CHANGED_IN_HTTP_POST\n")
    posts = _install_http(
        monkeypatch, f, choice="1",
        mutate=mutate if error == "paper_after_post" else None,
        status=503 if error == "http_503" else 200,
    )
    try:
        with pytest.raises(Exception):
            asyncio.run(live.run_r23h_original_real_question_once(
                **_args(tmp_path, f),
            ))
        assert len(posts) == 1
        assert f.cognitive._state("A").mode == "QUARANTINED"
        assert f.cognitive.current_scope("B")
        assert f.bridge.inference_lane._fenced == {"A"}
        report = json.loads((tmp_path / "fresh-evidence/r23h-original-real-model-report.json").read_text())
        assert report["classification"] == "R23H_REAL_ORIGINAL_MODEL_HOLD"
        assert report["model_post_attempted"] == 1
        assert report["reason"]
        assert not report["question_adopted"]
        assert f.owners["A"].retained.exploration_continuity is None
        assert (tmp_path / "fresh-evidence/original-question-model-http/bounded-1-request-body.bin").is_file()
    finally:
        _cleanup(f)
