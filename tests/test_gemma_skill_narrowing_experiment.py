import json

import pytest

import experiments.gemma_skill_narrowing as narrowing
from experiments.gemma_skill_narrowing import (
    BROAD_DISTRACTORS,
    CASES,
    ObservedLlamaCppProtocolFailure,
    ObservedLlamaCppProvider,
    build_request,
    build_schedule,
    dry_run_payload,
)
from relay_self.relay_engine import CognitionMode, DecisionStatus


def test_schedule_balances_broad_and_narrow() -> None:
    rows = build_schedule()
    assert len(rows) == 48

    for case in CASES:
        case_rows = [
            row for row in rows if row["case_id"] == case.case_id
        ]
        assert len(case_rows) == 12
        for condition in ("broad", "narrow"):
            condition_rows = [
                row
                for row in case_rows
                if row["condition"] == condition
            ]
            assert len(condition_rows) == 6
            assert {
                row["order_index"] for row in condition_rows
            } == {0, 1}


def test_narrowing_changes_only_context_surface() -> None:
    case = CASES[0]
    broad = build_request(case, condition="broad")
    narrow = build_request(case, condition="narrow")

    assert broad.request_id == narrow.request_id
    assert broad.instruction == narrow.instruction
    assert broad.intent_id == narrow.intent_id
    assert broad.focus == narrow.focus
    assert broad.choices == narrow.choices
    assert len(narrow.context) == 6
    assert len(broad.context) == 6 + len(BROAD_DISTRACTORS)
    assert broad.context[:6] == narrow.context


def test_dry_run_records_expected_matrix() -> None:
    payload = dry_run_payload()
    assert payload["measured_episode_count"] == 48
    assert payload["observations_per_case_condition"] == 6
    assert payload["broad_distractor_count"] == len(BROAD_DISTRACTORS)


def _fake_response_body(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                    "reasoning_content": "captured-side-channel",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 101,
            "completion_tokens": 17,
            "total_tokens": 118,
        },
        "timings": {"prompt_ms": 1.0},
    }


def test_provider_preserves_wire_evidence_before_protocol_failure(
    monkeypatch,
) -> None:
    body = _fake_response_body("")
    body_text = json.dumps(body, separators=(",", ":"))

    def fake_post_json(endpoint, payload, *, timeout):
        del endpoint, payload, timeout
        return body, 200, body_text

    monkeypatch.setattr(narrowing, "_post_json", fake_post_json)
    provider = ObservedLlamaCppProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
    )

    with pytest.raises(
        ObservedLlamaCppProtocolFailure,
        match="think model content is not valid JSON",
    ) as captured:
        provider(
            build_request(CASES[0], condition="narrow"),
            mode=CognitionMode.THINK,
        )

    assert len(provider.records) == 1
    record = provider.records[0]
    assert captured.value.record == record
    assert record["http_status"] == 200
    assert record["raw_text"] == ""
    assert record["reasoning_content"] == "captured-side-channel"
    assert record["response_body_text"] == body_text
    assert record["finish_reason"] == "stop"
    assert record["completion_tokens"] == 17
    assert record["provider_status"] is None
    assert "think model content is not valid JSON" in str(
        record["protocol_error"]
    )


def test_provider_keeps_valid_think_semantics(monkeypatch) -> None:
    content = json.dumps(
        {
            "status": "unresolved",
            "choice_id": None,
            "rationale": "route fact is missing",
        },
        separators=(",", ":"),
    )
    body = _fake_response_body(content)
    body_text = json.dumps(body, separators=(",", ":"))

    def fake_post_json(endpoint, payload, *, timeout):
        del endpoint, payload, timeout
        return body, 200, body_text

    monkeypatch.setattr(narrowing, "_post_json", fake_post_json)
    provider = ObservedLlamaCppProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
    )

    decision = provider(
        build_request(CASES[0], condition="narrow"),
        mode=CognitionMode.THINK,
    )

    assert decision.status is DecisionStatus.UNRESOLVED
    assert decision.choice_id is None
    assert decision.reason == "route fact is missing"
    assert len(provider.records) == 1
    assert "protocol_error" not in provider.records[0]
