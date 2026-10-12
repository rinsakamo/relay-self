"""S6 controlled native-target intervention contracts, offline synthetic-only.

No Minecraft, Java, Mineflayer, model, real Action or actual user permission.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer import self_s6_controlled_trial as s6
from adapters.mineflayer.self_continuous_host import AppendOnlySessionEvents
from adapters.mineflayer.self_s6_intervention import (
    CONFIRM,
    CONTROLLED_COMMAND,
    S6ControlledIntervention,
    S6ControlledPlan,
    S6InterventionRejected,
)
from test_self_continuous_host import _fixture

FAKE_FUTURE_REFERENCE = (
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-987654321"
)


class NativeServerStdin:
    def __init__(self, *, error: Exception | None = None):
        self.chunks = []
        self.drains = 0
        self.error = error

    def write(self, payload):
        self.chunks.append(payload)

    async def drain(self):
        self.drains += 1
        if self.error:
            raise self.error


def _native_controller(tmp_path, *, stdin=None):
    original = s42._pair()[3]
    spawn = replace(original, seq=2, kind="spawn")
    events = AppendOnlySessionEvents(tmp_path / "events.jsonl", spawn.session_id)
    server = SimpleNamespace(returncode=None, stdin=stdin or NativeServerStdin())
    controller = S6ControlledIntervention(
        S6ControlledPlan(FAKE_FUTURE_REFERENCE), spawn, events,
    )
    return controller, server, events


def _rows(tmp_path):
    return [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]


def test_controlled_target_submitted_once_without_native_evidence_claim(tmp_path):
    controller, server, events = _native_controller(tmp_path)
    events.write("session_started")
    asyncio.run(controller.submit_once(server))
    assert server.stdin.drains == 1
    assert server.stdin.chunks == [(CONTROLLED_COMMAND + "\n").encode()]
    assert "NoAI:1b" in CONTROLLED_COMMAND
    assert controller.attempted is True
    with pytest.raises(S6InterventionRejected, match="twice"):
        asyncio.run(controller.submit_once(server))
    rows = _rows(tmp_path)
    assert [x["kind"] for x in rows] == [
        "session_started", "controlled_target_submission_intent",
        "controlled_target_stdin_drained_unconfirmed",
    ]
    assert rows[1]["native_spawn_source"] == controller.spawn.provenance.reference
    assert rows[1]["authority_reference"] == FAKE_FUTURE_REFERENCE
    assert all(not r.get("command_executed_attested", False) for r in rows)
    assert all(not r.get("target_native_observed", False) for r in rows)
    assert all(not r.get("action_authorized", False) for r in rows)
    assert all(not r.get("natural_spawn_claimed", False) for r in rows)


def test_uncertain_stdin_after_write_is_not_a_second_target(tmp_path):
    broken = NativeServerStdin(error=OSError("hypothetical broken pipe"))
    controller, server, events = _native_controller(tmp_path, stdin=broken)
    events.write("session_started")
    with pytest.raises(OSError):
        asyncio.run(controller.submit_once(server))
    assert controller.attempted
    assert len(server.stdin.chunks) == 1
    assert [row["kind"] for row in _rows(tmp_path)] == [
        "session_started", "controlled_target_submission_intent",
    ]
    with pytest.raises(S6InterventionRejected):
        asyncio.run(controller.submit_once(server))


def test_original_l0_action_pipeline_stays_independent_of_one_start_hook(tmp_path):
    driver, probe, grant, execute, requests, source = _fixture(tmp_path)
    callback_count = []

    async def submit():
        callback_count.append("control-target-before-native")
        driver.events.write("controlled_target_stdin_drained_unconfirmed",
                            command_executed_attested=False,
                            target_native_observed=False,
                            action_authorized=False)

    res = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_session_started=submit,
    ))
    assert res["events"] == 2
    assert res["action_requests"] == res["closed_outcomes"] == 1
    assert callback_count == ["control-target-before-native"]
    assert requests == [1, 3] and source.calls == 2
    rows = [
        json.loads(row) for row in
        (tmp_path / "events.jsonl").read_text().splitlines()
    ]
    assert [r["kind"] for r in rows][:2] == [
        "session_started", "controlled_target_stdin_drained_unconfirmed",
    ]
    assert [r["kind"] for r in rows].count("action_outcome") == 1


def test_start_failure_is_unknown_without_native_action_or_restart(tmp_path):
    driver, probe, grant, execute, requests, source = _fixture(tmp_path)
    calls = []

    async def failed():
        calls.append(1)
        raise OSError("hypothetical submission failure")

    with pytest.raises(OSError):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
            on_session_started=failed,
        ))
    assert calls == [1] and source.calls == 0 and requests == []
    rows = [
        json.loads(row) for row in
        (tmp_path / "events.jsonl").read_text().splitlines()
    ]
    assert [r["kind"] for r in rows] == ["session_started", "session_failed"]
    assert rows[-1]["no_replay"] is True


@pytest.mark.parametrize("reference", [
    "", "https://github.com/rinsakamo/relay-self/issues/537",
    "https://github.com/other/repo/issues/537#issuecomment-123",
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-0",
])
def test_operator_reference_is_record_not_permission(reference):
    with pytest.raises(S6InterventionRejected):
        S6ControlledPlan(reference)


def test_dry_run_cannot_launch_or_check_host(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail("dry-run must have zero host effects")

    monkeypatch.setattr(s6.s1, "preflight", forbidden)
    monkeypatch.setattr(s6, "assess_qualified_rsee_world", forbidden)
    monkeypatch.setattr(s6.asyncio, "run", forbidden)
    assert s6.main([]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["classification"] == "S6_DRY_RUN_NO_EFFECTS"
    assert row["controlled_commands"] == row["actions"] == 0


def test_physical_flags_without_fresh_authority_fail_before_host(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail("unapproved request cannot inspect World or start anything")

    monkeypatch.setattr(s6.s1, "preflight", forbidden)
    monkeypatch.setattr(s6, "assess_qualified_rsee_world", forbidden)
    assert s6.main([
        "--run-disposable", "--confirm", CONFIRM,
        "--standing-eula-confirmed",
    ]) == 2
    assert "S6_OPERATOR_AUTHORITY_MISSING" in capsys.readouterr().out


def test_source_shaped_mock_full_authorization_still_not_physical(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    out.mkdir()
    invokes = []

    def qualified(*args):
        invokes.append("preflight")
        return object()

    def world(*args):
        invokes.append("native-rule")
        return SimpleNamespace(classification="FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED")

    async def not_real_run(binding, path, budget, *, controlled_target):
        invokes.append("mock-run")
        assert path == out
        assert isinstance(controlled_target, S6ControlledPlan)
        assert budget.max_actions == 3 and budget.max_frames == 500
        return {"node_exit": 0, "server_exit": 0,
                "frames": 0, "events": 0, "closed_outcomes": 0}

    monkeypatch.setattr(s6.s1, "preflight", qualified)
    monkeypatch.setattr(s6, "assess_qualified_rsee_world", world)
    monkeypatch.setattr(s6.s1, "run_physical", not_real_run)
    assert s6.main([
        "--run-disposable", "--confirm", CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference", FAKE_FUTURE_REFERENCE,
        "--output-dir", str(out),
    ]) == 0
    assert invokes == ["preflight", "native-rule", "mock-run"]
    row = json.loads(capsys.readouterr().out)
    assert row["classification"] == "S6_ONE_CONTROLLED_SESSION_TERMINATED_NOT_AUTONOMY_PROOF"
    assert row["controlled_target_native_identity_attested"] is False
    assert row["natural_spawn_claimed"] is False


def test_wrong_world_rule_never_calls_physical_driver(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(s6.s1, "preflight", lambda *_: object())
    monkeypatch.setattr(s6, "assess_qualified_rsee_world", lambda *_: SimpleNamespace(
        classification="NATURAL_MOB_SPAWNING_RULE_ENABLED_TARGET_UNPROVEN",
    ))
    monkeypatch.setattr(s6.s1, "run_physical", lambda *_a, **_k:
                        pytest.fail("must not call physical runner"))
    assert s6.main([
        "--run-disposable", "--confirm", CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference", FAKE_FUTURE_REFERENCE,
        "--output-dir", str(out),
    ]) == 2
    assert "S6_UNKNOWN_OR_BLOCKED" in capsys.readouterr().out


def test_cannot_increase_bounds_for_controlled_trial(monkeypatch, capsys):
    monkeypatch.setattr(s6.s1, "preflight", lambda *_:
                        pytest.fail("no preflight beyond physical bounds"))
    assert s6.main([
        "--run-disposable", "--confirm", CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference", FAKE_FUTURE_REFERENCE,
        "--output-dir", "/tmp/s6-unmaterialized-operator-path",
        "--max-actions", "4",
    ]) == 2
    assert "S6_UNKNOWN_OR_BLOCKED" in capsys.readouterr().out
