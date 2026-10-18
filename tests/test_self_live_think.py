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


# SelfWorld #633 Stage I: opt-in native live-probe -> read-only L1/HABIT and
# existing S60 single-attempt L2. All native probes in these tests are synthetic.


def scoped_world_probe(seq: int, *, label: str = "zombie", entity_id: int = 42):
    source = native_probe(seq, 4.0)
    fact = replace(
        source.snapshot.nearby_entities[0], entity_id=entity_id, name=label,
    )
    return replace(source, snapshot=replace(
        source.snapshot, nearby_entities=(fact,),
    ))


def test_live_selfworld_prediction_mismatch_is_read_by_l1_and_l2_but_not_action():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True,
            )
            await observer.observe(scoped_world_probe(8))
            assert observer.model_attempts == 0
            assert server.requests == 0
            # Same native entity ID, changed positive observed label. A
            # deterministic persistence hypothesis can be contradicted.
            await observer.observe(scoped_world_probe(19, label="skeleton"))
            await asyncio.sleep(.12)
            assert observer.model_attempts == 1
            assert server.requests == 1
            payload = server.posts[0]["messages"][1]["content"]
            assert '"status": "mismatch"' in payload
            assert '"observed_value": "skeleton"' in payload
            assert '"predicted_value": "zombie"' in payload
            assert '"preconfigured_l1_cognitive_candidate": "RECHECK"' in payload
            # Later native source invalidates a previously admitted L2 reply.
            await observer.observe(scoped_world_probe(47, label="skeleton"))
            receipt = await observer.close()
            assert receipt["self_world_live"] is True
            assert receipt["self_world_review_status"] == "mismatch"
            assert receipt["self_world_review_reason"] == "observed_prediction_mismatch"
            assert receipt["self_world_prior_source"] == "present:s15-session:8:s49-actual:s15-session:event-7"
            assert receipt["self_world_after_source"] == "present:s15-session:19:s49-actual:s15-session:event-18"
            assert receipt["preconfigured_l1_cognitive_candidate"] == "RECHECK"
            assert receipt["self_world_l2_input_bound"] is True
            assert receipt["model_attempts"] == 1
            assert receipt["text_current"] is False
            assert receipt["authorized_actions"] == 0
            assert receipt["l2_used_as_action"] is False
            assert receipt["learning_updates"] == 0
            assert receipt["habit_grants"] == 0
            assert receipt["l0_blocked_on_l2"] is False

    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_live_selfworld_unseen_target_is_undetermined_not_absent():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True,
            )
            await observer.observe(scoped_world_probe(8))
            missing = scoped_world_probe(19)
            missing = replace(missing, snapshot=replace(
                missing.snapshot, nearby_entities=(),
                nearby_entities_coverage=replace(
                    missing.snapshot.nearby_entities_coverage,
                    candidate_count=0, truncated=True,
                ),
            ))
            await observer.observe(missing)
            await asyncio.sleep(.12)
            assert server.requests == 1
            receipt = await observer.close()
            assert receipt["self_world_review_status"] == "undetermined"
            assert receipt["self_world_review_reason"] == "target_or_property_unobserved"
            assert receipt["preconfigured_l1_cognitive_candidate"] is None
            assert receipt["self_world_l2_input_bound"] is True
            assert receipt["authorized_actions"] == 0
            prompt = server.posts[0]["messages"][1]["content"]
            assert '"observed_value": null' in prompt
            assert '"coverage_truncated": true' in prompt
            assert '"status": "undetermined"' in prompt

    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_live_selfworld_no_second_owner_or_cross_session_replay():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=1,
                self_world_live=True,
            )
            await observer.observe(scoped_world_probe(8))
            with pytest.raises(ValueError, match="foreign/replayed"):
                await observer.observe(scoped_world_probe(8))
            foreign = replace(scoped_world_probe(19), session_id="foreign")
            with pytest.raises(ValueError, match="foreign/replayed"):
                await observer.observe(foreign)
            assert observer.model_attempts == 0
            await observer.observe(scoped_world_probe(19))
            await asyncio.sleep(.12)
            receipt = await observer.close()
            assert server.requests == 1
            assert receipt["self_world_review_status"] == "match"
            assert receipt["preconfigured_l1_cognitive_candidate"] == "OBSERVE"
            assert receipt["authorized_actions"] == 0
            assert receipt["learning_updates"] == 0

    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_selfworld_live_mode_requires_explicit_native_l2_opt_in(capsys):
    assert self_demo.main(["--self-world-live"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "SELF_WORLD_REQUIRES_LIVE_L2"
    assert self_demo.main(["--smoke", "--self-world-live"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "SELF_WORLD_REQUIRES_LIVE_L2"
    assert self_demo.main(["--live-think", "--self-world-live"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "LIVE_L2_REQUIRES_NATIVE_WORLD"


def test_live_selfworld_unqualified_optional_projection_never_interrupts_l0():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=1,
                self_world_live=True,
            )
            malformed = scoped_world_probe(8)
            malformed = replace(malformed, snapshot=replace(
                malformed.snapshot,
                nearby_entities_coverage=replace(
                    malformed.snapshot.nearby_entities_coverage,
                    candidate_count=0,
                ),
            ))
            # Optional L2 sidecar rejects malformed coverage, but the single
            # real S49 L0 owner need not wait on an advisory model.
            await observer.observe(malformed)
            assert observer.model_attempts == 0
            resumed = []
            async def owned_l0_step():
                resumed.append("L0_UNCHANGED")
            await asyncio.wait_for(owned_l0_step(), .1)
            receipt = await observer.close()
            assert resumed == ["L0_UNCHANGED"]
            assert receipt["status"] == "SELF_WORLD_INPUT_UNQUALIFIED"
            assert server.requests == 0
            assert receipt["authorized_actions"] == 0
            assert receipt["learning_updates"] == 0

    asyncio.run(asyncio.wait_for(scenario(), 6))
