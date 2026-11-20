"""D9 CPU-offline DEV: original B Owner + actual B GPU lane, HTTP stub only.

The HTTP server below is a deterministic TEST DOUBLE, NOT real Gemma,
Paper, Native, GPU or Source-owned physical execution. Model-selected
'1'/'2' comes through the actual B ResidentLlamaInferenceLane.submit path.
"""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.cognitive_minimal_dev import initial_patterns, initial_patterns_with_move
from relay_self.exploration_continuity_dev import (
    AttemptPhase,
    ExplorationContinuityError,
    open_question_refs,
)
from relay_self.exploration_d9_original_l1_dev import (
    D9OriginalL1Hold,
    form_d9_native_exploration_round,
    retain_d9_question_without_model,
    run_d9_original_bounded_l1,
)
from relay_self.exploration_d9_original_source_cut_dev import (
    D9SourceCutHold,
    verify_d9_original_owner_sources,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from test_exploration_goal_dev_v01 import d5_actual_stage28_resident
from test_exploration_stage28_d6_dev import _synthetic_native_probe


class _D9SyntheticBackend:
    def __init__(self, *, choice="1"):
        self.choice = choice
        self.posts = []
        self.probes = 0
        self.lock = threading.Lock()
        self.server = None
        self.thread = None

    def start(self):
        tester = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path != "/slots":
                    self.send_error(404)
                    return
                with tester.lock:
                    tester.probes += 1
                self.write_json([{"id": 0, "id_task": -1, "is_processing": False}])

            def do_POST(self):
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                payload = json.loads(self.rfile.read(
                    int(self.headers.get("Content-Length", "0")),
                ))
                with tester.lock:
                    tester.posts.append(payload)
                self.write_json({
                    "choices": [{
                        "message": {"content": json.dumps({
                            "status": "resolved", "choice_id": tester.choice,
                        })},
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": 30, "completion_tokens": 9,
                        "total_tokens": 39,
                    },
                })

            def write_json(self, payload):
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True,
        )
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat/completions"

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=3)


def _fixture(tmp_path):
    owners, resident, sources = d5_actual_stage28_resident(tmp_path)
    # A/B must have innate exploratory schema installed by the original
    # source-owning Self bootstrap, before any native World/body observation.
    for owner in owners.values():
        owner.pattern_registry = initial_patterns_with_move()
    probes = {}
    for sid, owner in owners.items():
        probe = _synthetic_native_probe(
            self_id=sid, native="native-live-" + sid, tick=100,
        )
        owner.current_worldbody_observation = probe
        probes[sid] = probe
    return owners, resident, probes


def _lane(resident, endpoint):
    provider = LlamaCppRelayProvider(
        endpoint=endpoint, model="synthetic-d9-test", timeout=4.0,
    )
    witness = LlamaCppSingleSlotWitness(
        provider=provider, backend_ref="synthetic-single-GPU-slot",
    )
    return ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=resident, witness=witness,
    )


def test_d9_source_qualified_real_owner_round_does_not_invent_target(tmp_path):
    owners, resident, probes = _fixture(tmp_path)
    for sid in ("A", "B"):
        source = form_d9_native_exploration_round(
            owners[sid], resident, probes[sid],
            world_session_id="paper-owned-d9",
        )
        assert source.scope.self_id == sid
        assert source.question_ref.startswith(
            "question:unobserved-world:" + sid + ":",
        )
        assert source.round_.proposals[0].route == "NEEDS_L2"
        assert source.round_.proposals[0].target_refs == ()
        assert source.round_.frame.options == ()
        assert tuple(source.round_.l1.numbered) == (
            ("1", "ESCALATE_L2"), ("2", "DEFER"),
        )
        assert source.round_.need.intensity > .2
        assert source.physical_action_issue_authorized is False
        assert owners[sid].retained.exploration_continuity is None
        assert not owners[sid].pending_questions


@pytest.mark.parametrize("choice,phase", [
    ("1", AttemptPhase.RESERVED), ("2", None),
])
def test_d9_real_original_llama_lane_one_http_choice_persists_only_l1_selection(
    tmp_path, choice, phase,
):
    owners, resident, probes = _fixture(tmp_path)
    fake = _D9SyntheticBackend(choice=choice)
    endpoint = fake.start()
    lane = _lane(resident, endpoint)
    try:
        outcome = asyncio.run(run_d9_original_bounded_l1(
            owners["A"], resident, lane, probes["A"],
            world_session_id="paper-owned-d9", timeout_s=8.0,
        ))
        state = load_persistent_cognition(
            owners["A"].files.cognition_file,
        )
        assert state == owners["A"].retained
        assert state.exploration_continuity is not None
        assert state.exploration_continuity.self_id == "A"
        assert open_question_refs(state, expected_self_id="A") == (
            outcome.question_ref,
        )
        assert outcome.model_status == "resolved"
        assert outcome.model_choice_id == choice
        assert outcome.selected_status == (
            "ESCALATE_L2" if choice == "1" else "DEFER"
        )
        assert outcome.l2_model_invoked is False
        assert outcome.physical_action_issue_authorized is False
        assert len(fake.posts) == 1
        assert fake.probes >= 2
        assert fake.posts[0]["model"] == "synthetic-d9-test"
        if phase is None:
            assert outcome.attempted_l2_ref is None
            assert state.exploration_continuity.attempts == ()
        else:
            assert outcome.attempted_l2_ref is not None
            assert len(state.exploration_continuity.attempts) == 1
            assert state.exploration_continuity.attempts[0].phase is phase
        assert owners["B"].retained.exploration_continuity is None
    finally:
        fake.close()


def test_d9_nonnative_or_stale_original_owner_rejected_before_gpu(tmp_path):
    owners, resident, probes = _fixture(tmp_path)
    source = form_d9_native_exploration_round(
        owners["A"], resident, probes["A"],
        world_session_id="paper-owned-d9",
    )
    assert source.question_ref
    owner = owners["A"]
    owner.pattern_registry = initial_patterns()
    with pytest.raises(D9OriginalL1Hold, match="innate exploration"):
        form_d9_native_exploration_round(
            owner, resident, probes["A"],
            world_session_id="paper-owned-d9",
        )
    owner.pattern_registry = initial_patterns_with_move()
    other = probes["B"]
    with pytest.raises(D9OriginalL1Hold, match="current WorldBody"):
        form_d9_native_exploration_round(
            owner, resident, other,
            world_session_id="paper-owned-d9",
        )
    resident.fence_self("A")
    with pytest.raises(D9OriginalL1Hold, match="ONLINE"):
        form_d9_native_exploration_round(
            owner, resident, probes["A"],
            world_session_id="paper-owned-d9",
        )


def test_d9_only_original_native_world_probe_may_be_l1_source(tmp_path):
    owners, resident, probes = _fixture(tmp_path)
    owner = owners["A"]
    owner.current_worldbody_observation = SimpleNamespace(
        session_id="native-live-A", request_id=probes["A"].request_id,
    )
    with pytest.raises(D9OriginalL1Hold):
        form_d9_native_exploration_round(
            owner, resident, probes["A"],
            world_session_id="paper-owned-d9",
        )
    assert owner.retained.exploration_continuity is None
    assert owner.pending_questions == set()


def test_d9_same_question_old_attempt_blocks_second_gpu_model_call(
    tmp_path,
):
    owners, resident, probes = _fixture(tmp_path)
    backend = _D9SyntheticBackend(choice="1")
    endpoint = backend.start()
    lane = _lane(resident, endpoint)
    try:
        first = asyncio.run(run_d9_original_bounded_l1(
            owners["A"], resident, lane, probes["A"],
            world_session_id="paper-owned-d9", timeout_s=8.0,
        ))
        assert first.attempted_l2_ref is not None
        # Source-owned D Question ledger refuses duplicate before any
        # second original GPU submission; no synthetic extra L1 inference.
        with pytest.raises(ExplorationContinuityError, match="already registered"):
            asyncio.run(run_d9_original_bounded_l1(
                owners["A"], resident, lane, probes["A"],
                world_session_id="paper-owned-d9", timeout_s=8.0,
            ))
        assert len(backend.posts) == 1
        state = load_persistent_cognition(owners["A"].files.cognition_file)
        assert len(state.exploration_continuity.attempts) == 1
    finally:
        backend.close()



def test_d9_original_a_question_only_b_real_bounded_source_cut(tmp_path):
    owners, resident, probes = _fixture(tmp_path)
    a = retain_d9_question_without_model(
        owners["A"], resident, probes["A"],
        world_session_id="paper-owned-d9",
    )
    assert a.l1_model_invoked is False
    backend = _D9SyntheticBackend(choice="1")
    endpoint = backend.start()
    try:
        b = asyncio.run(run_d9_original_bounded_l1(
            owners["B"], resident, _lane(resident, endpoint),
            probes["B"], world_session_id="paper-owned-d9",
            timeout_s=8.0,
        ))
        assert len(backend.posts) == 1
        result = verify_d9_original_owner_sources(owners, (a, b))
        assert tuple(x.self_id for x in result) == ("A", "B")
        assert result[0].l1_selected_status == "NOT_INFERRED"
        assert result[0].l1_model_invoked is False
        assert result[0].genuine_attempt_refs == ()
        assert result[1].l1_selected_status == "ESCALATE_L2"
        assert result[1].l1_model_invoked is True
        assert result[1].genuine_attempt_refs == (b.attempted_l2_ref,)
        assert all(not x.physical_action_issue_authorized for x in result)
    finally:
        backend.close()


@pytest.mark.parametrize("choice", ["2", "1"])
def test_d9_before_typed_paper_cut_holds_b_defer_or_changed_source(
    tmp_path, choice,
):
    owners, resident, probes = _fixture(tmp_path)
    a = retain_d9_question_without_model(
        owners["A"], resident, probes["A"],
        world_session_id="paper-owned-d9",
    )
    fake = _D9SyntheticBackend(choice=choice)
    endpoint = fake.start()
    try:
        b = asyncio.run(run_d9_original_bounded_l1(
            owners["B"], resident, _lane(resident, endpoint),
            probes["B"], world_session_id="paper-owned-d9",
            timeout_s=8.0,
        ))
        if choice == "2":
            with pytest.raises(D9SourceCutHold, match="no original Self"):
                verify_d9_original_owner_sources(owners, (a, b))
            assert owners["B"].retained.exploration_continuity.attempts == ()
        else:
            owners["B"].pending_questions.clear()
            with pytest.raises(D9SourceCutHold, match="Question"):
                verify_d9_original_owner_sources(owners, (a, b))
        assert len(fake.posts) == 1
    finally:
        fake.close()


def test_d9_real_paper_source_producer_requires_model_preflight_before_world(
    tmp_path, monkeypatch,
):
    from experiments import stage28_d9_real_source_dev as producer

    kw = {
        "paper_jar": tmp_path / "paper.jar",
        "paper_sha256": "a" * 64,
        "plugin_jar": tmp_path / "plugin.jar",
        "plugin_sha256": "b" * 64,
        "scratch_parent": tmp_path,
        "accepted_eula": True,
        "real_world_dev_grant": True,
        "d9_source_exploration_dev": True,
        "typed_owner_cut_dev": True,
        "real_llm_grant": True,
        "llama_endpoint": "http://127.0.0.1:8080/v1/chat/completions",
        "systemone_endpoint": "http://127.0.0.1:8080/v1/systemone",
        "model_name": "synthetic-test-not-real-gemma",
    }
    def forbidden(**_kwargs):
        pytest.fail("World PRE_WORLD HOLD bypassed and attempted Paper preflight")
    monkeypatch.setattr(producer, "preflight_two_native", forbidden)
    with pytest.raises(producer.RealResidentPresenceRefusal, match="GGUF/GPU proof"):
        asyncio.run(producer.run_real_resident_presence(**kw))
    assert list(tmp_path.iterdir()) == []

    # Controlled, synthetic typed receipt only proves that the pre-World
    # conditional can reach the next original B source preflight. It is NOT
    # an attested GPU model or permission to create an actual World.
    from experiments.stage24g_model_gate_dev import Stage24gModelGateReceipt

    class PreflightReached(Exception):
        pass

    def blocked(**_kwargs):
        raise PreflightReached

    monkeypatch.setattr(producer, "preflight_two_native", blocked)
    receipt = Stage24gModelGateReceipt(
        5555, kw["model_name"], "/synthetic/fake.gguf", "c" * 64,
        "synthetic RTX", "d" * 64, "e" * 64, 0, 1, "f" * 64,
    )
    with pytest.raises(PreflightReached):
        asyncio.run(producer.run_real_resident_presence(
            **kw, stage24g_model_receipt=receipt,
        ))
    assert list(tmp_path.iterdir()) == []


def test_d9_source_runner_main_with_no_actual_model_refuses_before_world(
    tmp_path, monkeypatch,
):
    import sys

    from experiments import stage28_d9_real_source_dev as producer

    monkeypatch.setattr(sys, "argv", [
        "D9",
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--paper-sha256", "a" * 64,
        "--plugin-jar", str(tmp_path / "plugin.jar"),
        "--plugin-sha256", "b" * 64,
        "--scratch-parent", str(tmp_path),
        "--eula-accepted", "--real-world-dev-grant",
        "--grant-real-llm", "--d9-source-exploration-dev",
        "--typed-owner-cut-dev",
    ])
    assert producer.main() == 2
    assert list(tmp_path.iterdir()) == []


def test_d9_resident_trial_hashlib_does_not_depend_on_legacy_move_branch():
    """D9 hashes the Paper source before the optional legacy MOVE branch."""
    from experiments.stage28_d9_real_source_dev import _owned_resident_trial

    assert "hashlib" not in _owned_resident_trial.__code__.co_varnames
    assert _owned_resident_trial.__globals__["hashlib"].sha256(b"paper").hexdigest() == (
        "382635c9325bf3273d195ff1b8a44e5b11afd7d97addeb8863ea35feb98c1a07"
    )
