"""S Lane S1 integration preflight and natural-World-only negative tests.

No Java, Node, Minecraft, GPU, LLM or network access in this suite.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer import self_s1_runtime as s1
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.self_continuous_host import (
    AppendOnlySessionEvents,
    BoundedSessionDriver,
    SessionBudget,
    SessionRunRejected,
)


def test_cli_default_is_pure_dry_run(monkeypatch, capsys):
    def never_run(*args, **kwargs):
        raise AssertionError("dry-run must not start Python asyncio or World")

    monkeypatch.setattr(s1.asyncio, "run", never_run)
    assert s1.main([]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["classification"] == "S1_DRY_RUN_NO_EFFECTS"
    assert row["world"] == "NOT_STARTED"
    assert row["action"] == "NOT_ISSUED"


@pytest.mark.parametrize("flags", [
    ["--run-disposable"],
    ["--run-disposable", "--confirm", s1.CONFIRM],
    ["--run-disposable", "--standing-eula-confirmed"],
])
def test_no_world_with_partial_operator_authority(flags, monkeypatch, capsys):
    monkeypatch.setattr(
        s1, "preflight",
        lambda *a: pytest.fail("preflight was reached without all opt-ins"),
    )
    assert s1.main(flags) == 2
    assert "AUTHORITY_MISSING" in capsys.readouterr().out


def test_opted_cli_rejects_missing_output_before_any_launch(monkeypatch, capsys):
    monkeypatch.setattr(
        s1.asyncio, "run",
        lambda *a, **kw: pytest.fail("run_physical must not be reached"),
    )
    flags = [
        "--run-disposable", "--confirm", s1.CONFIRM,
        "--standing-eula-confirmed",
    ]
    assert s1.main(flags) == 2
    assert "OUTPUT_DIR_MISSING" in capsys.readouterr().out


def test_canonical_rsee_manifest_filenames():
    jar, snapshot, manifest, initial, npm = s1.runtime_inputs()
    assert jar.name == "minecraft-1.21.8.jar"
    assert snapshot.name == "snapshot"
    assert manifest.name == "snapshot_manifest.json"
    assert initial.name == "initial_native_observation.json"
    assert npm.name == "npm-mineflayer-4.39.0"


def test_missing_shared_rsee_fails_before_process(tmp_path):
    with pytest.raises(SessionRunRejected, match="canonical"):
        s1.preflight(tmp_path / "absent", tmp_path)


def test_preexisting_output_does_not_get_overwritten(tmp_path, monkeypatch):
    root = tmp_path / "external-shared"
    root.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    (output / "session_events.jsonl").write_text("sealed")
    monkeypatch.setattr(s1, "RSEE", root)
    with pytest.raises(SessionRunRejected, match="new empty"):
        s1.preflight(root, output)
    assert (output / "session_events.jsonl").read_text() == "sealed"


def test_non_target_native_observation_never_probes_or_issues(tmp_path):
    retained, _, _, near_event, _ = s42._pair()
    sid = near_event.session_id
    snapshot = replace(near_event.snapshot, nearby_entities=())
    event = replace(near_event, snapshot=snapshot, seq=1)
    host = NormalWorldL0(sid, "escape-threat", retained, max_events=1,
                         max_action_requests=1)
    budget = SessionBudget(max_events=1, max_actions=1, max_frames=1,
                           max_seconds=2, poll_seconds=.02)
    sink = AppendOnlySessionEvents(tmp_path / "session_events.jsonl", sid)

    class Source:
        started = SimpleNamespace(session_id=sid)
        calls = 0

        async def receive(self):
            self.calls += 1
            return event

    source = Source()
    driver = BoundedSessionDriver(host, source, budget, sink)

    async def forbidden(*args, **kwargs):
        raise AssertionError("no natural zombie should create a probe or Action")

    def forbidden_grant(*args):
        raise AssertionError("no qualified World action allowed")

    result = asyncio.run(driver.run(
        probe=forbidden, grant=forbidden_grant, on_action=forbidden,
    ))
    assert result["terminal"] == "FRAME_BUDGET_ENDED"
    assert result["events"] == 0 and result["action_requests"] == 0
    assert source.calls == 1
    rows = [
        json.loads(line)
        for line in (tmp_path / "session_events.jsonl").read_text().splitlines()
    ]
    assert [r["kind"] for r in rows] == ["session_started", "session_terminal"]


def test_explicit_s49_foreground_callbacks_have_one_probe_owner(monkeypatch):
    sid = "world-one"
    seen = []
    fake_probe = SimpleNamespace(seq=9, request_id="s49-actual:world-one:event-8")

    async def correlated(session, request_id):
        seen.append(("probe", request_id))
        return fake_probe

    monkeypatch.setattr(s1, "_correlated_observe", correlated)
    session = SimpleNamespace(started=SimpleNamespace(session_id=sid))
    host = SimpleNamespace(session_id=sid)
    executor = SimpleNamespace()
    probe, grant, on_action = s1.s49_callbacks(session, host, executor)
    assert callable(grant) and callable(on_action)
    event = SimpleNamespace(seq=8)
    reading = asyncio.run(probe(event))
    assert reading is fake_probe
    assert seen == [("probe", "s49-actual:world-one:event-8")]


def test_invalid_budgets_fail_before_session():
    with pytest.raises(SessionRunRejected):
        SessionBudget(max_seconds=float("inf"))
