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
    snapshot = replace(
        near_event.snapshot, nearby_entities=(),
        nearby_entities_coverage=replace(
            near_event.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    )
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


@pytest.mark.parametrize("node_shutdown_fails", [False, True])
def test_fake_owned_world_closes_processes_and_evidence_without_action(
    tmp_path, monkeypatch, node_shutdown_fails,
):
    """Mock every process/World boundary; never run native dependencies."""
    source = s42._pair()[3]
    output = tmp_path / "output"
    output.mkdir()
    shutdown_order = []

    class FakeSession:
        started = SimpleNamespace(session_id=source.session_id)

        async def receive(self):
            return replace(
                source,
                snapshot=replace(
                    source.snapshot, nearby_entities=(),
                    nearby_entities_coverage=replace(
                        source.snapshot.nearby_entities_coverage, candidate_count=0,
                    ),
                ),
            )

        async def shutdown(self, **kwargs):
            shutdown_order.append("node")
            if node_shutdown_fails:
                raise RuntimeError("mock node cleanup failed")
            return 0

        async def terminate(self):
            if not node_shutdown_fails:
                pytest.fail("normal fake shutdown never terminates by force")
            shutdown_order.append("node-terminate")
            raise RuntimeError("mock terminate failed")

    class FakeServer:
        returncode = None

    server = FakeServer()
    async def fake_ready(*args):
        shutdown_order.append("server-start")
        return server, None, None

    async def fake_shutdown(server_arg, collector):
        assert server_arg is server
        shutdown_order.append("server-stop")
        server.returncode = 0

    async def fake_spawn(session_arg):
        assert isinstance(session_arg, FakeSession)

    async def fake_launch(*args, **kwargs):
        shutdown_order.append("node-start")
        return FakeSession()

    monkeypatch.setattr(s1, "prepare_stopped_world", lambda *a, **k: {})
    monkeypatch.setattr(s1, "_ready_server", fake_ready)
    monkeypatch.setattr(s1, "_shutdown_server", fake_shutdown)
    monkeypatch.setattr(s1, "_await_spawn", fake_spawn)
    monkeypatch.setattr(s1.MineflayerProcessSession, "launch", fake_launch)
    monkeypatch.setattr(s1, "NativeObservationOnly", lambda session: session)
    monkeypatch.setattr(s1, "RSEE", tmp_path / "shared-root")
    budget = SessionBudget(max_events=1, max_actions=1, max_frames=1,
                           max_seconds=2, poll_seconds=.02)
    result = asyncio.run(s1.run_physical(object(), output, budget))
    assert result["events"] == result["action_requests"] == 0
    expected = ["server-start", "node-start", "node"]
    if node_shutdown_fails:
        expected.append("node-terminate")
    expected.append("server-stop")
    assert shutdown_order == expected
    cleanup = json.loads((output / "owned_cleanup.json").read_text())
    assert cleanup["native_stop_ack"] is False
    assert cleanup["gpu_release_claimed"] is False
    assert cleanup["server_exit"] == 0
    assert cleanup["node_cleanup_unconfirmed"] is node_shutdown_fails
    if node_shutdown_fails:
        assert cleanup["node_exit"] is None
        assert cleanup["node_terminate_error_type"] == "RuntimeError"
    else:
        assert cleanup["node_exit"] == 0
    assert not list(output.glob("*.pid"))



def test_s49_native_callback_forwards_original_probe_and_separate_stage_grants(
    monkeypatch,
):
    """An admitted S49 selection reaches the existing executor, not a new issuer."""
    retained, near, _, near_event, _ = s42._pair()
    sid = near_event.session_id
    event = replace(near_event, seq=3)
    reading = replace(near.observation, seq=4)
    session = SimpleNamespace(started=SimpleNamespace(session_id=sid))
    host = NormalWorldL0(
        sid, "escape-threat", retained, max_events=2, max_action_requests=1,
    )
    called = []

    async def correlated(owner, request_id):
        assert owner is session
        called.append(("correlated", request_id))
        return reading

    async def existing_execute(owner, step, bound, probe, propose, issue):
        assert owner is session
        assert probe is reading and bound == "already-admitted-binding"
        assert propose.stage.value == "PROPOSE"
        assert issue.stage.value == "ISSUE"
        assert propose.action_id == issue.action_id == step.action_request_id
        assert propose.session_id == issue.session_id == sid
        assert propose.event_seq == issue.event_seq == event.seq
        assert propose.probe_seq == issue.probe_seq == reading.seq
        assert propose.authority_id != issue.authority_id
        assert propose.provenance != issue.provenance
        called.append(("existing-executor", step.action_request_id))
        return "ORIGINAL_TYPED_RECEIPT_SENTINEL"

    executor = SimpleNamespace(intent=object(), execute=existing_execute)
    monkeypatch.setattr(s1, "_correlated_observe", correlated)
    monkeypatch.setattr(
        s1, "_native_threat",
        lambda observation, request_id, **kwargs: SimpleNamespace(distance_m=2),
    )
    state = {}

    def epoch(supervisor, intent, owner, supplied, *, expected_revision, native):
        assert owner is retained and supplied is retained
        assert expected_revision == retained.revision and native.distance_m == 2
        state["admission"] = True
        return (
            {
                "plan": SimpleNamespace(selected=SimpleNamespace(candidate_id="MOVE_AWAY")),
                "admission": SimpleNamespace(status=SimpleNamespace(value="admitted")),
                "control": object(), "route": object(),
                "policies": ("unused", "native-admission-policy", "last"),
            },
            SimpleNamespace(cognition_requested=False),
        )

    monkeypatch.setattr(s1, "_native_epoch_two", epoch)
    monkeypatch.setattr(
        s1, "resolve_execution_binding",
        lambda *args, **kwargs: "already-admitted-binding",
    )
    probe, grant, on_action = s1.s49_callbacks(session, host, executor)

    async def run():
        fresh = await probe(event)
        assert fresh is reading
        choice = host._check(event, fresh)
        assert choice.selection.value == "MOVE_AWAY"
        step = host.decide(event, fresh, grant=grant(choice, event.seq))
        return await on_action(step)

    receipt = asyncio.run(run())
    assert receipt == "ORIGINAL_TYPED_RECEIPT_SENTINEL"
    assert state["admission"]
    assert called == [
        ("correlated", f"s49-actual:{sid}:event-{event.seq}"),
        ("existing-executor", f"s49-native-move-{event.seq}"),
    ]
