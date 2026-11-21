from pathlib import Path

import pytest

from adapters.llama_cpp.qualify_relay_engine import (
    LlamaCppQualificationError,
    LlamaCppRuntimeIdentity,
    RepositoryIdentity,
)
from experiments.qualify_present_relay_engine_seam import (
    qualify_present_relay_seam,
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


def _runtime() -> LlamaCppRuntimeIdentity:
    return LlamaCppRuntimeIdentity(
        origin="http://127.0.0.1:1234",
        health_status="ok",
        model="gemma-local",
        build_info="b10874-e2d2c0d6a",
        model_alias="gemma-local",
        model_path="/models/gemma.gguf",
        model_ftype="Q4_K - Medium",
    )


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        head="a" * 40,
        tree="b" * 40,
    )


def test_qualification_reports_present_projection_and_skill_handoff() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave")]
    )

    report = qualify_present_relay_seam(
        RelayEngine(provider),
        _runtime(),
        _repository(),
    )

    assert report.qualified is True
    assert report.evidence_class == "model_or_system_quality"
    assert report.broad_fact_count == 9
    assert report.local_fact_count == 7
    assert report.request_intent_id == "intent-reach-safety"
    assert report.request_focus == "FLEE"
    assert report.choice_id == "cave"
    assert report.broadened is False
    assert report.reprojected is False
    assert report.skill_id == "FLEE"
    assert report.skill_intent_id == "intent-reach-safety"
    assert report.skill_state == "started"
    assert report.open_action_count == 0
    assert "hunger" not in report.context_keys
    assert "companion_speaking" not in report.context_keys
    assert "shelter:cave" in report.context_keys
    assert "shelter:ridge" in report.context_keys
    assert provider.modes == [CognitionMode.BOUNDED]


def test_qualification_rejects_wrong_present_backed_choice() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("ridge")]
    )

    with pytest.raises(
        LlamaCppQualificationError,
        match="unexpected destination",
    ):
        qualify_present_relay_seam(
            RelayEngine(provider),
            _runtime(),
            _repository(),
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
        qualify_present_relay_seam(
            RelayEngine(provider),
            _runtime(),
            _repository(),
        )


def test_launcher_owns_source_layout_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (
        repo_root
        / "experiments"
        / "run_present_relay_engine_seam_qualification.sh"
    ).read_text(encoding="utf-8")

    assert (
        'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"'
        in launcher
    )
    assert 'REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"' in launcher
    assert (
        'export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"'
        in launcher
    )
    assert (
        "exec python3 -B -m "
        'experiments.qualify_present_relay_engine_seam "$@"'
        in launcher
    )
