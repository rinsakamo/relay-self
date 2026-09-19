from unittest.mock import patch

import pytest

from adapters.llama_cpp.qualify_relay_engine import (
    LlamaCppQualificationError,
    LlamaCppRuntimeIdentity,
    RepositoryIdentity,
    inspect_llama_cpp_runtime,
    inspect_repository,
    qualify_relay_engine,
)
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngine,
)


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.modes: list[CognitionMode] = []

    def __call__(self, _request, *, mode: CognitionMode) -> ProviderDecision:
        self.modes.append(mode)
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        return self.decisions.pop(0)


def runtime() -> LlamaCppRuntimeIdentity:
    return LlamaCppRuntimeIdentity(
        origin="http://127.0.0.1:1234",
        health_status="ok",
        model="gemma-local",
        build_info="llama.cpp build 10874",
        model_alias="gemma-local",
        model_path="/models/gemma.gguf",
        model_ftype="Q4_K - Medium",
    )


def repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        head="a" * 40,
        tree="b" * 40,
    )


def test_qualification_accepts_expected_real_decision_semantics() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave")]
    )

    report = qualify_relay_engine(
        RelayEngine(provider),
        runtime(),
        repository(),
    )

    assert report.qualified is True
    assert report.evidence_class == "model_or_system_quality"
    assert report.final_status == "resolved"
    assert report.choice_id == "cave"
    assert report.expected_choice_id == "cave"
    assert report.escalated is False
    assert report.intent_id == "intent-reach-safety"
    assert report.skill_state == "started"
    assert report.open_action_count == 0
    assert provider.modes == [CognitionMode.BOUNDED]


def test_qualification_records_explicit_think_when_bounded_is_unresolved() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.resolved(
                "cave",
                reason="shelter dominates at night",
            ),
        ]
    )

    report = qualify_relay_engine(
        RelayEngine(provider),
        runtime(),
        repository(),
    )

    assert report.qualified is True
    assert report.escalated is True
    assert [attempt["mode"] for attempt in report.attempts] == [
        "bounded",
        "think",
    ]
    assert report.attempts[-1]["reason"] == "shelter dominates at night"


def test_qualification_rejects_wrong_resolved_choice() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("ridge")]
    )

    with pytest.raises(
        LlamaCppQualificationError,
        match="unexpected choice",
    ):
        qualify_relay_engine(
            RelayEngine(provider),
            runtime(),
            repository(),
        )


def test_qualification_rejects_final_unresolved_result() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded"),
            ProviderDecision.unresolved(reason="think"),
        ]
    )

    with pytest.raises(
        LlamaCppQualificationError,
        match="remained unresolved",
    ):
        qualify_relay_engine(
            RelayEngine(provider),
            runtime(),
            repository(),
        )


def test_repository_inspection_requires_clean_checkout(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    with patch(
        "adapters.llama_cpp.qualify_relay_engine._run_git",
        side_effect=["", "a" * 40 + "\n", "b" * 40 + "\n"],
    ):
        identity = inspect_repository(tmp_path)

    assert identity.head == "a" * 40
    assert identity.tree == "b" * 40


def test_repository_inspection_rejects_dirty_checkout(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    with patch(
        "adapters.llama_cpp.qualify_relay_engine._run_git",
        return_value="?? __pycache__/\n",
    ):
        with pytest.raises(
            LlamaCppQualificationError,
            match="clean RelaySelf checkout",
        ):
            inspect_repository(tmp_path)


def test_runtime_inspection_requires_one_healthy_served_model() -> None:
    responses = [
        {"status": "ok"},
        {"data": [{"id": "gemma-local"}]},
        {
            "build_info": "llama.cpp build 10874",
            "model_alias": "gemma-local",
            "model_path": "/models/gemma.gguf",
            "model_ftype": "Q4_K - Medium",
        },
    ]

    with patch(
        "adapters.llama_cpp.qualify_relay_engine._get_json",
        side_effect=responses,
    ) as get_json:
        identity = inspect_llama_cpp_runtime(
            origin="http://127.0.0.1:1234/",
            timeout=1.0,
        )

    assert identity.origin == "http://127.0.0.1:1234"
    assert identity.health_status == "ok"
    assert identity.model == "gemma-local"
    assert identity.model_ftype == "Q4_K - Medium"
    assert get_json.call_count == 3


def test_runtime_inspection_rejects_multiple_models() -> None:
    with patch(
        "adapters.llama_cpp.qualify_relay_engine._get_json",
        side_effect=[
            {"status": "ok"},
            {"data": [{"id": "a"}, {"id": "b"}]},
        ],
    ):
        with pytest.raises(
            LlamaCppQualificationError,
            match="exactly one",
        ):
            inspect_llama_cpp_runtime(
                origin="http://127.0.0.1:1234",
                timeout=1.0,
            )
