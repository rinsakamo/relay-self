import subprocess
from pathlib import Path


def _script() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "run_present_relay_engine_owned_runtime_qualification.sh"
    )


def test_owned_runtime_wrapper_has_valid_shell_syntax() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(_script())],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_owned_runtime_wrapper_owns_server_lifetime_and_cleanup() -> None:
    text = _script().read_text(encoding="utf-8")

    assert 'LLAMA_PID=$!' in text
    assert 'trap cleanup EXIT INT TERM' in text
    assert 'kill "$LLAMA_PID"' in text
    assert 'wait "$LLAMA_PID"' in text
    assert 'kill -0 "$LLAMA_PID"' in text


def test_owned_runtime_wrapper_waits_for_health_before_qualification() -> None:
    text = _script().read_text(encoding="utf-8")

    readiness = text.index('"$ORIGIN/health"')
    launcher = text.index(
        '"$CANONICAL_LAUNCHER" \\\n  --repo-root'
    )

    assert readiness < launcher
    assert '"status"[[:space:]]*:[[:space:]]*"ok"' in text
    assert 'llama.cpp exited before health readiness' in text


def test_owned_runtime_wrapper_records_runtime_attestation() -> None:
    text = _script().read_text(encoding="utf-8")

    assert '"$ORIGIN/health"' in text
    assert '"$ORIGIN/props"' in text
    assert '"$ORIGIN/v1/models"' in text
    assert 'expected exactly one served model id' in text
    assert 'model-sha256.txt' in text
    assert 'nvidia-smi.txt' in text


def test_owned_runtime_wrapper_invokes_canonical_launcher_once() -> None:
    text = _script().read_text(encoding="utf-8")

    invocation = (
        '"$CANONICAL_LAUNCHER" \\\n'
        '  --repo-root "$REPO_ROOT" \\\n'
        '  --origin "$ORIGIN" \\\n'
        '  --timeout "$TIMEOUT"'
    )
    assert text.count(invocation) == 1
    assert "canonical-launcher-invocations.txt" in text


def test_owned_runtime_wrapper_does_not_call_provider_directly() -> None:
    text = _script().read_text(encoding="utf-8")

    assert "/v1/chat/completions" not in text
