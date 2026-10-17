"""Product in-World L2 side-tap: async mocked loopback, genuine typed probes.

No Java, GPU, real GGUF, Minecraft server or native Action in this CI suite.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerPosition,
)
from adapters.mineflayer.self_live_think import LiveL2Observer
from test_action_feedback_qualification import observation
from test_self_demo import _native_report
from test_self_think import OneShotLocalModel


def native_probe(seq: int, distance: float, *, sid: str = "s15-session"):
    prior = observation(seq, 0.0, 0.0)
    entity = MineflayerEntityFact(
        entity_id=seq, name="zombie", entity_type="mob",
        distance=distance,
        position=MineflayerPosition(distance, 64, 0),
    )
    snap = replace(
        prior.snapshot, nearby_entities=(entity,),
        nearby_entities_coverage=replace(
            prior.snapshot.nearby_entities_coverage, candidate_count=1,
        ),
    )
    return replace(
        prior, session_id=sid, snapshot=snap,
        request_id=f"s49-actual:{sid}:event-{seq-1}",
    )


def test_live_observer_l2_model_inflight_does_not_block_native_l0():
    async def scenario():
        async with OneShotLocalModel() as server:
            owner = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
            )
            await owner.observe(native_probe(8, 10.0))
            # Independent L0 can progress while model is being queried.
            complete = []
            async def existing_l0():
                complete.append("L0_RUNNING")
                return "ACTUAL_L0_OWNER_ISSUES_ACTION_SEPARATELY"
            assert await asyncio.wait_for(existing_l0(), .1)
            assert complete == ["L0_RUNNING"]
            await asyncio.sleep(.12)
            assert server.requests == 1
            await owner.observe(native_probe(19, 2.0))
            await owner.observe(native_probe(47, 2.0))
            row = await owner.close()
            assert server.requests == 1
            assert row["model_attempts"] == 1
            assert row["source_world_seq"] == 8
            assert row["latest_world_seq"] == 47
            assert row["native_observations_seen"] == 3
            assert row["text_current"] is False
            assert row["status"] == "EXPIRED_WORLD_ADVANCED"
            assert row["authorized_actions"] == 0
            assert row["l2_used_as_action"] is False
            assert row["learning_updates"] == 0
            assert row["habit_grants"] == 0
            assert row["backend_stop_ack"] is False
            assert row["gpu_release_verified"] is False
            assert len(server.posts) == 1
            payload = server.posts[0]
            assert "zombie 10" in payload["messages"][1]["content"]
            assert "commands" in payload["messages"][1]["content"]
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_native_probe_source_scope_and_replay_denied():
    async def scenario():
        async with OneShotLocalModel() as server:
            owner = LiveL2Observer(model="self-demo-test-model", port=server.port)
            with pytest.raises(ValueError):
                await owner.observe(observation(1, 0, 0))  # not a correlated probe
            await owner.observe(native_probe(8, 10))
            with pytest.raises(ValueError):
                await owner.observe(native_probe(8, 10))  # replay
            with pytest.raises(ValueError):
                await owner.observe(native_probe(19, 2, sid="other-session"))
            row = await owner.close()
            assert row["model_attempts"] == 1
            with pytest.raises(ValueError):
                await owner.observe(native_probe(47, 2))
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_world_model_error_still_does_not_grant_action():
    async def scenario():
        async with OneShotLocalModel(status=503) as server:
            owner = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=1,
            )
            await owner.observe(native_probe(8, 10))
            await asyncio.sleep(.12)
            await owner.observe(native_probe(19, 2))
            row = await owner.close()
            assert server.requests == 1
            assert row["authorized_actions"] == 0
            assert row["l2_used_as_action"] is False
            assert not row["text_current"]
            assert row["model_binary_identity_verified"] is False
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_live_flag_is_never_enabled_without_real_world_or_model(capsys, tmp_path):
    for args, reason in (
        (["--live-think"], "LIVE_L2_REQUIRES_NATIVE_WORLD"),
        (["--smoke", "--live-think"], "LIVE_L2_REQUIRES_NATIVE_WORLD"),
        (["--run-disposable", "--think", "--live-think"],
         "TWO_MODEL_ATTEMPTS_DENIED"),
    ):
        assert self_demo.main(args) == 2
        assert json.loads(capsys.readouterr().out)["reason"] == reason


def test_explicit_live_mode_uses_original_s49_owner_and_retains_one_sidecar(
    capsys, monkeypatch, tmp_path: Path,
):
    async def scenario():
        async with OneShotLocalModel() as server:
            import adapters.mineflayer.s49_normal_session_real_ci as s49

            async def fake_original_s49(report_path, log_path, *, live_probe=None):
                assert live_probe is not None
                for seq, distance in ((8, 10.0), (19, 2.0), (47, 2.0)):
                    await live_probe(native_probe(
                        seq, distance, sid="real-native-session-test-record",
                    ))
                    await asyncio.sleep(.06)
                report_path.write_text(json.dumps(_native_report()), encoding="utf-8")
                log_path.write_text("mock-no-minecraft", encoding="utf-8")
                return 0

            monkeypatch.setattr(s49, "qualify", fake_original_s49)
            monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/mock/java-or-node")
            args = [
                "--run-disposable", "--confirm", self_demo.CONFIRM,
                "--output-dir", str(tmp_path), "--live-think",
                "--model-alias", "self-demo-test-model", "--model-port", str(server.port),
                "--model-timeout", "2",
            ]
            rc = await asyncio.to_thread(self_demo.main, args)
            assert rc == 0
            assert server.requests == 1
            rows = [
                json.loads(line) for line in
                (tmp_path / "self_trace.jsonl").read_text().splitlines()
            ]
            assert [row["kind"] for row in rows].count("l2_live_observer") == 1
            assert rows[-2]["kind"] == "l2_live_observer"
            assert rows[-2]["authorized_actions"] == 0
            assert rows[-2]["text_current"] is False
            assert rows[-1]["kind"] == "observed_memory"
            assert rows[-1]["retained_episodes"] == 2
            assert (tmp_path / "live_l2.jsonl").is_file()
            from relay_self.persistent_cognition import load_persistent_cognition
            assert len(load_persistent_cognition(
                tmp_path / "observed_memory.json",
            ).memories) == 2

    asyncio.run(asyncio.wait_for(scenario(), 6))
    assert "l2_live_observer" in capsys.readouterr().out
