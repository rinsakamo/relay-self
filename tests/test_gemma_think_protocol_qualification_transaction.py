from pathlib import Path

from experiments.gemma_think_protocol_qualification_transaction import (
    _experiment_command,
    validate_payload,
)


def _payload(qualification: str) -> dict[str, object]:
    provider_call: dict[str, object] = {
        "mode": "think",
        "http_status": 200,
        "prompt_tokens": 538,
        "completion_tokens": 44,
        "provider_status": "unresolved",
        "provider_choice_id": None,
        "finish_reason": "stop",
        "request_hash": "request",
        "response_hash": "response",
        "response_body_sha256": "wire",
    }
    if qualification == "INVALID_PROTOCOL":
        provider_call.update(
            {
                "provider_status": None,
                "protocol_error": "invalid JSON",
                "response_body_text": "{\"choices\":[]}",
            }
        )
    return {
        "evidence_class": (
            "actual-model gemma think protocol qualification"
        ),
        "qualification": qualification,
        "model_generation_calls": 1,
        "surface": {
            "case_id": "cave_only",
            "candidate_key": "route_open:cave",
        },
        "provider_call": provider_call,
    }


def test_validate_accepts_valid_protocol_evidence() -> None:
    result = validate_payload(_payload("VALID_PROTOCOL"))
    assert result["qualification"] == "VALID_PROTOCOL"
    assert result["model_generation_calls"] == 1


def test_validate_accepts_lossless_invalid_protocol_evidence() -> None:
    result = validate_payload(_payload("INVALID_PROTOCOL"))
    assert result["qualification"] == "INVALID_PROTOCOL"
    assert result["protocol_error"] == "invalid JSON"


def test_experiment_command_is_one_probe_surface() -> None:
    command = _experiment_command(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
        output_path=Path("/tmp/result.json"),
        run=True,
    )

    assert command[1:4] == [
        "-B",
        "-m",
        "experiments.gemma_think_protocol_qualification",
    ]
    assert "--run" in command


def test_canonical_launcher_owns_source_layout_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (
        repo_root
        / "experiments"
        / "run_gemma_think_protocol_qualification_transaction.sh"
    ).read_text(encoding="utf-8")

    assert 'REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"' in launcher
    assert (
        'export PYTHONPATH="$REPO_ROOT/src'
        '${PYTHONPATH:+:$PYTHONPATH}"'
    ) in launcher
    assert (
        "experiments.gemma_think_protocol_qualification_transaction"
        in launcher
    )
