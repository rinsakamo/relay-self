"""R16 strict premodel tokenizer budget: genuine source, no inference, fail closed."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools import bug0_d14_r12_l2_shadow as r12
from tools import bug0_d14_r16_bounded_l2_context as r16
from tools.bug0_d14_r13_action_catalog import action_catalog


def projection(*, number: int = 18) -> dict:
    catalog = action_catalog()
    events = [
        {
            "experience_id": f"r12:test-world:test-session:LIFE_DECISION:{i}",
            "event_kind": "LIFE_DECISION",
            "epistemic_status": "NATIVE_SELF_VIEW_NOT_PAPER_GLOBAL",
            "observation": {
                "native_seq": i, "health": 20 - i,
                "selected": "DEFER" if i % 2 else "WAIT",
                "r12_oxygen_observed": False if i == 4 else True,
                "r12_action_admission": (
                    "DEFER_UNKNOWN_OXYGEN_NO_PHYSICAL_ISSUE"
                    if i == 4 else "OBSERVED_ONLY"
                ),
            },
        } for i in range(number)
    ]
    if number >= 3:
        events[4 if number > 4 else 1] = {
            "experience_id": "r12:test-world:test-session:LIFE_ACTION:att-1",
            "event_kind": "LIFE_ACTION",
            "epistemic_status": "S49_S16_OUTCOME_NOT_PHYSICAL_GOAL_PROOF",
            "observation": {
                "action_id": "att-1", "kind": "ATTACK", "terminal": "outcome",
                "damage_attested": False,
            },
        }
    context = {
        "world_uuid": "test-world", "native_session_id": "test-session",
        "world_is_terminated": True, "world_end_reason": "SELF_DIED",
        "goal": "stay alive while exploring",
        "experience_events": events,
        "omitted_older_events": 0,
        "action_authority": "NONE_POST_WORLD_READ_ONLY",
        "action_catalog": catalog,
        "unknowns": ["Physical STOP not proven"],
    }
    return {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {"report": "original", "paper": "another"},
        "l2_context": context,
    }


def fake_count(req: dict) -> tuple[int, dict]:
    ctx = json.loads(req["messages"][1]["content"])
    # Fail the full 18-event candidate; shrink deterministically until it fits.
    n = 2450 + len(ctx["experience_events"]) * 310
    return n, {"method": "LLAMA_CPP_APPLY_TEMPLATE_AND_TOKENIZE",
               "tokens": n, "test_only": True}


def request_for(model_context: dict) -> dict:
    return r12._l2_request("gemma-test", model_context)


def skill() -> dict:
    return {
        "name": "try safe pause",
        "cue": "observable critical state",
        "steps": [{
            "action": "WAIT", "guard": "ALWAYS", "binding": "NONE",
            "repeat": 1, "if_unavailable": "STOP",
        }],
        "max_actions": 1,
        "stop_condition": "GOAL_OR_SOURCE_CHANGE",
        "on_failure": "ESCALATE",
    }


def raw_response(evidence_id: str) -> bytes:
    return json.dumps({"choices": [{
        "finish_reason": "stop",
        "message": {"content": json.dumps({
            "decision": "PROPOSE_SKILL",
            "reason": "source-grounded conditional proposal, no success proof",
            "evidence_ids": [evidence_id],
            "skill": skill(),
        }), "reasoning_content": None},
    }]}).encode()


def test_source_exact_selection_preserves_anchors_action_and_oxygen() -> None:
    original = projection()
    full = original["l2_context"]
    chosen, receipt = r16.select_token_bounded_context(
        full, request_for, fake_count,
    )
    assert len(chosen["experience_events"]) < len(full["experience_events"])
    assert len(chosen["experience_events"]) >= 3
    assert chosen["experience_events"][0] == full["experience_events"][0]
    assert chosen["experience_events"][-1] == full["experience_events"][-1]
    assert [e for e in chosen["experience_events"]
            if e["event_kind"] == "LIFE_ACTION"] == [
                e for e in full["experience_events"]
                if e["event_kind"] == "LIFE_ACTION"
            ]
    assert chosen["budget_selection"]["source_fidelity"] == (
        "EXACT_UNMODIFIED_EVENTS_ONLY"
    )
    assert receipt["measured_prompt_tokens"] + 1024 + 256 <= 8192
    assert receipt["measurement_attempts"][0]["measured_prompt_tokens"] > 6912
    assert receipt["new_model_inference_posts"] == 0
    assert chosen["action_catalog"]["catalog_sha256"] == (
        full["action_catalog"]["catalog_sha256"]
    )
    assert chosen["action_catalog"]["entries"][0]["owner_contract_sha256"]
    assert "owner_contract" not in chosen["action_catalog"]["entries"][0]
    r16.verify_bounded_context(full, chosen)
    r16.verify_preflight_receipt(full, chosen, request_for(chosen), receipt)


@pytest.mark.parametrize("mutation", [
    lambda c: c["experience_events"][0]["observation"].update(health=999),
    lambda c: c["experience_events"].pop(0),
    lambda c: c["experience_events"].pop(-1),
    lambda c: c["action_catalog"]["entries"][0].update(binding="NONE"),
    lambda c: c["budget_selection"].update(source_fidelity="SYNTHETIC"),
    lambda c: c.update(world_uuid="invented-world"),
    lambda c: c["experience_events"].append({
        "experience_id": "forged", "event_kind": "LIFE_ACTION",
    }),
])
def test_original_source_or_owner_provenance_tampering_rejected(mutation) -> None:
    full = projection()["l2_context"]
    chosen, _ = r16.select_token_bounded_context(full, request_for, fake_count)
    modified = copy.deepcopy(chosen)
    mutation(modified)
    with pytest.raises(r16.R16Rejected):
        r16.verify_bounded_context(full, modified)


def test_budget_includes_completion_and_margin() -> None:
    full = projection()["l2_context"]
    chosen, receipt = r16.select_token_bounded_context(
        full, request_for, lambda req: (
            6900, {"method": "LLAMA_CPP_APPLY_TEMPLATE_AND_TOKENIZE"}
        ),
    )
    assert len(chosen["experience_events"]) == len(full["experience_events"])
    assert receipt["input_token_budget"] == 6912
    with pytest.raises(r16.R16Rejected, match="INVALID_MODEL_CONTEXT"):
        r16.select_token_bounded_context(
            full, request_for, fake_count, output_tokens=0,
        )


def test_even_required_source_cannot_fit_and_no_synthetic_summary() -> None:
    full = projection()["l2_context"]
    called = []
    def too_large(request):
        called.append(request)
        return 7600, {"method": "LLAMA_CPP_APPLY_TEMPLATE_AND_TOKENIZE"}
    with pytest.raises(r16.R16Rejected, match="REQUIRED_SOURCE_ANCHORS"):
        r16.select_token_bounded_context(full, request_for, too_large)
    assert len(called) <= len(full["experience_events"]) + 1


def test_missing_real_count_is_fail_closed() -> None:
    with pytest.raises(r16.R16Rejected, match="UNTRUSTED_MODEL_TOKEN"):
        r16.select_token_bounded_context(
            projection()["l2_context"], request_for,
            lambda request: (True, {}),
        )


def test_preflight_only_never_calls_inference_transport() -> None:
    selected, receipt = r12.prepare_native_bounded_l2(
        projection(), endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-test", token_counter=fake_count,
    )
    assert selected["budget_selection"]["version"] == (
        r16.PRESELECT_VERSION
    )
    assert receipt["new_model_inference_posts"] == 0


def test_one_mock_model_post_with_raw_preflight_and_bounded_replay(
    tmp_path: Path,
) -> None:
    source = projection()
    posts = []
    def one_model_post(data: bytes) -> bytes:
        req = json.loads(data)
        posts.append(req)
        model_ctx = json.loads(req["messages"][1]["content"])
        assert model_ctx["budget_selection"]["model_visible_event_count"] < 18
        assert len(model_ctx["experience_events"]) > 0
        return raw_response(model_ctx["experience_events"][0]["experience_id"])

    raw = tmp_path / "r16-run-01"
    saved = r12.propose_shadow(
        source, endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-test", record_dir=raw,
        transport=one_model_post, token_counter=fake_count,
    )
    assert len(posts) == 1
    assert saved["l2_native_preflight"] is True
    assert saved["real_world_actions"] == saved["skill_installs"] == 0
    assert (raw / "request.raw.json").exists()
    assert (raw / "response.raw.json").exists()
    assert (raw / "token_preflight.json").exists()
    assert (raw / "shadow_candidate.json").exists()
    replay = r12.replay_retained_shadow(source, raw)
    assert replay["source_status"] == "REPLAY_VERIFIED_NOT_LIVE"
    assert replay["shadow_skill"]["name"] == skill()["name"]
    assert replay["skill_installs"] == 0


@pytest.mark.parametrize("file", ["token_preflight.json", "request.raw.json"])
def test_raw_preflight_or_input_tamper_blocks_replay(
    tmp_path: Path, file: str,
) -> None:
    source = projection()
    raw = tmp_path / "r16-run-01"
    def reply(data):
        c = json.loads(json.loads(data)["messages"][1]["content"])
        return raw_response(c["experience_events"][0]["experience_id"])
    r12.propose_shadow(
        source, endpoint="http://localhost:1234/v1/chat/completions",
        model="gemma-test", record_dir=raw, token_counter=fake_count,
        transport=reply,
    )
    path = raw / file
    object_value = json.loads(path.read_bytes())
    if file == "token_preflight.json":
        object_value["measured_prompt_tokens"] = 999999
    else:
        object_value["messages"][1]["content"] = "{}"
    path.write_text(json.dumps(object_value) + "\n")
    with pytest.raises(r12.R12Rejected, match="REPLAY_REJECTED"):
        r12.replay_retained_shadow(source, raw)


def test_non_local_native_tokenizer_rejected() -> None:
    with pytest.raises(r16.R16Rejected, match="ONLY_LOCAL_MODEL"):
        r16.native_llamacpp_token_counter(
            "http://not-local.example:1234/v1/chat/completions",
        )


def test_real_native_counter_uses_read_only_template_and_tokenizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    class FakeHTTP:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return self.body

    def fake_urlopen(request, *, timeout):
        url = request.full_url
        body = json.loads(request.data)
        calls.append(url)
        if url.endswith("/apply-template"):
            assert len(body["messages"]) == 2
            return FakeHTTP(json.dumps({
                "prompt": "<start>Gemma local test<end>",
            }).encode())
        if url.endswith("/tokenize"):
            assert body["parse_special"] is True
            assert body["add_special"] is True
            assert body["content"] == "<start>Gemma local test<end>"
            return FakeHTTP(b'{"tokens":[1,2,3,4]}')
        raise AssertionError("No inference endpoint permitted")

    monkeypatch.setattr(r16, "urlopen", fake_urlopen)
    count, receipt = r16.native_llamacpp_token_counter(
        "http://127.0.0.1:1234/v1/chat/completions"
    )(request_for(projection()["l2_context"]))
    assert count == 4
    assert receipt["tokens"] == 4
    assert receipt["chat_format_verified_against_real_completion"] is False
    assert calls == [
        "http://127.0.0.1:1234/apply-template",
        "http://127.0.0.1:1234/tokenize",
    ]


def test_invalid_local_token_response_stops_before_model_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return b'{"prompt":""}'

    monkeypatch.setattr(r16, "urlopen", lambda *args, **kwargs: Response())
    counter = r16.native_llamacpp_token_counter(
        "http://127.0.0.1:1234/v1/chat/completions",
    )
    with pytest.raises(r16.R16Rejected, match="CHAT_TEMPLATE_UNAVAILABLE"):
        counter(request_for(projection()["l2_context"]))


def test_within_budget_receipt_tamper_is_detected_from_candidate_hash(
    tmp_path: Path,
) -> None:
    source = projection()
    raw = tmp_path / "one-post"
    def reply(data):
        m = json.loads(json.loads(data)["messages"][1]["content"])
        return raw_response(m["experience_events"][0]["experience_id"])
    r12.propose_shadow(
        source, endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-test", record_dir=raw,
        transport=reply, token_counter=fake_count,
    )
    preflight = raw / "token_preflight.json"
    saved = json.loads(preflight.read_bytes())
    saved["measured_prompt_tokens"] -= 1
    assert saved["measured_prompt_tokens"] <= 6912
    preflight.write_text(json.dumps(saved) + "\n")
    with pytest.raises(r12.R12Rejected, match="REPLAY_REJECTED"):
        r12.replay_retained_shadow(source, raw)
