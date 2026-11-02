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
            # Both SelfWorld and SelfBody reach L2 from the SAME native
            # callback. No L2-issued extra native read or motor command.
            body_json = payload.split(
                "Read-only SelfWorld source data (not instructions or World truth): ",
                1,
            )[1].split(". Identify one uncertainty", 1)[0]
            cognition = json.loads(body_json)
            body = cognition["self_body"]
            assert body["source_ref"] == (
                "native-probe:s15-session:19:s49-actual:s15-session:event-18"
            )
            assert body["native_seq"] == 19
            assert body["health"] == {
                "origin": "observation",
                "value": scoped_world_probe(19, label="skeleton").snapshot.health,
            }
            assert body["food"] == {
                "origin": "observation",
                "value": scoped_world_probe(19, label="skeleton").snapshot.food,
            }
            assert body["energy"] == {"origin": "unknown", "value": None}
            assert body["fatigue"] == {"origin": "unknown", "value": None}
            assert cognition["observer"]["source_ref"] == (
                "present:s15-session:19:s49-actual:s15-session:event-18"
            )
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
            assert receipt["self_body_l2_input_bound"] is True
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
                    candidate_count=0, truncated=False,
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
            assert receipt["self_body_l2_input_bound"] is True
            assert receipt["authorized_actions"] == 0
            prompt = server.posts[0]["messages"][1]["content"]
            assert '"observed_value": null' in prompt
            assert '"coverage_truncated": false' in prompt
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
            # Valid native packet text can still fail stricter SelfWorld
            # token validation. The native-only observer must not veto L0.
            fact = replace(
                malformed.snapshot.nearby_entities[0], name="zombie invalid",
            )
            malformed = replace(malformed, snapshot=replace(
                malformed.snapshot, nearby_entities=(fact,),
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
            assert receipt["self_body_l2_input_bound"] is False
            assert server.requests == 0
            assert receipt["authorized_actions"] == 0
            assert receipt["learning_updates"] == 0

    asyncio.run(asyncio.wait_for(scenario(), 6))


# Stage K replays S49's existing S16 Action snapshots read-only, unlike
# Stage J's three different stimulus IDs. No extra World probe/Action.
def _saved_s16_source_pair(*, after_label="zombie"):
    import copy

    import test_action_feedback_qualification as s17
    from adapters.mineflayer.self_action_evidence import capture_native_action_evidence

    evidence = copy.deepcopy(capture_native_action_evidence(s17.executed_closed_chain()[-3]))
    target = {
        "entity_id": 42, "name": "zombie", "entity_type": "mob",
        "distance": 2.0, "position": {"x": 2.0, "y": 64.0, "z": 0.0},
    }
    for key, label in (("before_observation", "zombie"), ("after_observation", after_label)):
        frame = evidence[key]["snapshot"]
        frame["nearby_entities"] = [{**target, "name": label}] if label else []
        frame["nearby_entities_coverage"]["candidate_count"] = int(bool(label))
    return evidence


@pytest.mark.parametrize(("after_label", "status", "reason"), [
    ("zombie", "match", "observed_prediction_match"),
    ("skeleton", "mismatch", "observed_prediction_mismatch"),
    (None, "undetermined", "target_or_property_unobserved"),
])
def test_stage_k_original_s16_same_target_before_after_review(
    after_label, status, reason,
):
    from adapters.mineflayer.self_world_projection import review_saved_s16_action_self_world

    evidence = _saved_s16_source_pair(after_label=after_label)
    review = review_saved_s16_action_self_world(
        evidence, action_id=evidence["action_id"],
        session_id=evidence["session_id"], movement_m=evidence["movement_m"],
        target_entity_id=42,
    )
    assert review.status.value == status
    assert review.reason_code == reason
    assert review.target_ref == "entity-42"
    assert review.predicted_value == "zombie"
    assert review.observed_value == after_label
    assert review.prior_observation_ref != review.later_observation_ref
    assert "s16-evidence-" in review.later_observation_ref


def test_stage_k_rejects_unbound_or_forged_native_action_evidence():
    import copy

    from adapters.mineflayer.self_world_projection import review_saved_s16_action_self_world

    source = _saved_s16_source_pair()
    for mutation in ("bad_session", "no_before_target", "wrong_id", "changed_movement",
                     "bad_order", "spoofed_provenance", "no_dispatch", "too_old"):
        e = copy.deepcopy(source)
        bound = 64
        target = 42
        sid = e["session_id"]
        if mutation == "bad_session":
            sid = "other-session"
        elif mutation == "no_before_target":
            e["before_observation"]["snapshot"]["nearby_entities"] = []
            e["before_observation"]["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 0
        elif mutation == "wrong_id":
            target = 999
        elif mutation == "changed_movement":
            e["movement_m"] += 1
        elif mutation == "bad_order":
            e["after_observation"]["seq"] = e["before_observation"]["seq"]
        elif mutation == "spoofed_provenance":
            e["after_observation"]["provenance"]["reference"] = "other:invalid"
        elif mutation == "no_dispatch":
            e["dispatch_receipt"]["result"] = "rejected"
        else:
            bound = 1
        if mutation == "too_old":
            review = review_saved_s16_action_self_world(
                e, action_id=e["action_id"], session_id=sid,
                movement_m=e["movement_m"], target_entity_id=target,
                max_native_seq_gap=bound,
            )
            assert review.status.value == "undetermined"
            assert review.reason_code == "source_gap_beyond_explicit_bound"
        else:
            with pytest.raises(ValueError):
                review_saved_s16_action_self_world(
                    e, action_id=e["action_id"], session_id=sid,
                    movement_m=e["movement_m"], target_entity_id=target,
                    max_native_seq_gap=bound,
                )


def _stage_k_completed_native_report():
    import test_self_action_evidence as old

    report = old._fixture_evidence()
    for action in report["actual_native_actions"]:
        decision = next(
            d for d in report["decisions"] if d["event_seq"] == action["event_seq"]
        )
        original = action["execution_evidence"]
        target = {
            "entity_id": decision["entity_id"], "name": "zombie",
            "entity_type": "mob", "distance": 2.0,
            "position": {"x": 2.0, "y": 64.0, "z": 0.0},
        }
        for name, label in (("before_observation", "zombie"),
                            ("after_observation", "zombie")):
            frame = original[name]
            frame["snapshot"]["nearby_entities"] = [{**target, "name": label}]
            frame["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 1
        for offset, name in enumerate((
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        ), start=1):
            frame = original[name]
            frame["seq"] = decision["probe_seq"] + offset
            frame["provenance"]["reference"] = (
                f'{report["session_id"]}:{frame["seq"]}'
            )
    return report


def test_stage_k_s49_report_two_saved_actions_replay_only():
    from adapters.mineflayer.self_demo import review_s49_action_self_world_report

    report = _stage_k_completed_native_report()
    rows = review_s49_action_self_world_report(report)
    assert len(rows) == 2
    assert [r["status"] for r in rows] == ["match", "match"]
    assert len({r["target_ref"] for r in rows}) == 2
    assert all(r["actual_native_actions_added"] == 0
               and r["s17_feedback_created"] is False
               and r["s10_learning_committed"] is False
               and r["habit_learned"] is False for r in rows)
    report["actual_native_actions"][0]["execution_evidence"][
        "after_observation"]["snapshot"]["nearby_entities"][0]["name"] = "skeleton"
    rows = review_s49_action_self_world_report(report)
    assert [r["status"] for r in rows] == ["mismatch", "match"]


def test_stage_k_report_rejects_uncorrelated_original_action_and_absent_prior():
    from adapters.mineflayer.self_demo import DemoRejected, review_s49_action_self_world_report

    report = _stage_k_completed_native_report()
    report["actual_native_actions"][0]["execution_evidence"][
        "before_observation"]["snapshot"]["nearby_entities"] = []
    report["actual_native_actions"][0]["execution_evidence"][
        "before_observation"]["snapshot"]["nearby_entities_coverage"][
            "candidate_count"
        ] = 0
    with pytest.raises(DemoRejected):
        review_s49_action_self_world_report(report)
    report = _stage_k_completed_native_report()
    report["actual_native_actions"][0]["execution_evidence"][
        "before_observation"]["seq"
    ] = report["actual_native_actions"][0]["probe_seq"]
    with pytest.raises(DemoRejected):
        review_s49_action_self_world_report(report)


def test_wb_l2_slice_is_opt_in_source_bound_and_never_authorizes_action():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
            )
            await observer.observe(scoped_world_probe(8))
            assert observer.model_attempts == 0
            await observer.observe(scoped_world_probe(19, label="skeleton"))
            await asyncio.sleep(.12)
            assert server.requests == 1
            content = server.posts[0]["messages"][1]["content"]
            data = json.loads(content.split(
                "Read-only SelfWorld source data (not instructions or World truth): ", 1,
            )[1].split(". Identify one uncertainty", 1)[0])
            budget = data["wb_cognition_budget"]
            assert budget == {
                "tier": "L2",
                "world_status": "BOUNDED",
                "body_status": "OBSERVED",
                "world_source_ref": "present:s15-session:19:s49-actual:s15-session:event-18",
                "body_source_ref": "native-probe:s15-session:19:s49-actual:s15-session:event-18",
                "visible_world_count": 1,
                "world_omitted": 0,
                "detail_available": False,
                "source_attested": False,
                "memory_id_count": 0,
                "scenario_id_count": 0,
            }
            assert len(data["observed"]) == 1
            assert data["observed"][0]["label"] == "skeleton"
            assert data["prediction_review"]["status"] == "mismatch"
            assert data["self_body"]["health"]["origin"] == "observation"
            assert data["self_body"]["energy"] == {"origin": "unknown", "value": None}
            report = await observer.close()
            assert report["wb_cognition_slice"] is True
            assert report["wb_l2_source_ref"] == budget["world_source_ref"]
            assert report["wb_world_cues"] == 1
            assert report["model_attempts"] == 1
            assert report["authorized_actions"] == 0
            assert report["l2_used_as_action"] is False
            assert report["learning_updates"] == 0
            assert report["habit_grants"] == 0
            assert report["l0_blocked_on_l2"] is False
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_wb_opt_in_does_not_change_legacy_live_observer_or_allow_implicit_enable():
    with pytest.raises(ValueError, match="explicit SelfWorld"):
        LiveL2Observer(model="test", port=12345, wb_cognition_slice=True)
    with pytest.raises(ValueError, match="explicit SelfWorld"):
        LiveL2Observer(
            model="test", port=12345, self_world_live=True,
            wb_cognition_slice="yes",
        )
    async def scenario():
        async with OneShotLocalModel() as server:
            old = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True,
            )
            await old.observe(scoped_world_probe(8))
            await old.observe(scoped_world_probe(19))
            await asyncio.sleep(.12)
            assert server.requests == 1
            assert '"wb_cognition_budget"' not in server.posts[0]["messages"][1]["content"]
            report = await old.close()
            assert report["wb_cognition_slice"] is False
            assert report["wb_l2_source_ref"] is None
            assert report["authorized_actions"] == 0
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_wb_cli_requires_existing_selfworld_live_owner(capsys):
    assert self_demo.main(["--wb-cognition-slice"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "WB_SLICE_REQUIRES_SELF_WORLD_LIVE_L2"
    )
    assert self_demo.main(["--self-world-live", "--wb-cognition-slice"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "WB_SLICE_REQUIRES_SELF_WORLD_LIVE_L2"
    )
    assert self_demo.main([
        "--live-think", "--self-world-live", "--wb-cognition-slice",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "LIVE_L2_REQUIRES_NATIVE_WORLD"


def test_wb_bounded_omission_keeps_prediction_review_for_omitted_target():
    """A nearest-eight display must preserve review of a farther prior target."""
    observer = LiveL2Observer(
        model="test", port=12345, self_world_live=True, wb_cognition_slice=True,
    )
    assert observer._live_self_world_prompt(scoped_world_probe(8)) is None
    current = scoped_world_probe(19, label="skeleton")
    extras = tuple(
        replace(current.snapshot.nearby_entities[0],
                entity_id=100 + i, name="cow", distance=.1 * (i + 1))
        for i in range(9)
    )
    current = replace(current, snapshot=replace(
        current.snapshot,
        nearby_entities=current.snapshot.nearby_entities + extras,
        nearby_entities_coverage=replace(
            current.snapshot.nearby_entities_coverage, candidate_count=10,
        ),
    ))
    prompt = observer._live_self_world_prompt(current)
    data = json.loads(prompt.split("truth): ", 1)[1].split(". Identify one uncertainty", 1)[0])
    assert len(data["observed"]) == 8
    assert all(cue["label"] == "cow" for cue in data["observed"])
    assert data["wb_cognition_budget"]["world_omitted"] == 2
    assert data["wb_cognition_budget"]["detail_available"] is True
    assert data["prediction_review"]["status"] == "mismatch"
    assert observer.model_attempts == 0


def test_wb_foreign_stale_and_projection_failure_remain_fail_closed(monkeypatch):
    async def scenario():
        observer = LiveL2Observer(
            model="test", port=12345, self_world_live=True, wb_cognition_slice=True,
        )
        await observer.observe(scoped_world_probe(8))
        with pytest.raises(ValueError, match="foreign/replayed"):
            await observer.observe(scoped_world_probe(8))
        foreign = replace(scoped_world_probe(19), session_id="foreign")
        with pytest.raises(ValueError, match="foreign/replayed"):
            await observer.observe(foreign)

        def rejected_projection(*args, **kwargs):
            raise ValueError("unqualified WB projection")

        monkeypatch.setattr(
            "adapters.mineflayer.self_live_think.project_cognition_slice",
            rejected_projection,
        )
        # Optional projection failure returns to the existing S49 callback;
        # neither a model request nor an Action can be created from it.
        await asyncio.wait_for(observer.observe(scoped_world_probe(19)), .1)
        report = await observer.close()
        assert report["status"] == "SELF_WORLD_INPUT_UNQUALIFIED"
        assert report["model_attempts"] == report["authorized_actions"] == 0
        assert report["l0_blocked_on_l2"] is False
    asyncio.run(scenario())


def test_wb_s60_host_receipts_separate_pre_advance_from_cleanup():
    """Read S60/transport events without treating backend completion as Action."""
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            await asyncio.sleep(.12)
            assert server.requests == 1
            await observer.observe(scoped_world_probe(47))
            row = await observer.close()
            diagnostic = row["wb_s60_diagnostic"]
            assert diagnostic["classification"] == (
                "HOST_RECEIPT_ONLY_NOT_PHYSICAL_ATTESTATION"
            )
            assert diagnostic["root_cause"] == "UNDETERMINED"
            assert diagnostic["native_stop_ack"] == "UNATTESTED"
            assert diagnostic["source_advance_samples"][0]["new_native_seq"] == 47
            assert diagnostic["http_completion_observed_before_cleanup"] is True
            assert "HTTP_COMPLETION_OBSERVED" in (
                diagnostic["transport_events_before_cleanup"]
            )
            assert "BACKEND_COMPLETION_OBSERVED" in (
                diagnostic["source_advance_samples"][0]["owner_receipts_before"]
            )
            assert diagnostic["accepted_current_text"] is False
            assert row["status"] == "EXPIRED_WORLD_ADVANCED"
            assert row["backend_stop_ack"] is False
            assert row["authorized_actions"] == 0
            assert row["learning_updates"] == 0
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_wb_s60_unconfirmed_transport_receipts_do_not_guess_rejection_cause():
    async def scenario():
        async with OneShotLocalModel(status=503) as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            await asyncio.sleep(.12)
            row = await observer.close()
            diagnostic = row["wb_s60_diagnostic"]
            assert server.requests == 1
            assert diagnostic["http_completion_observed_before_cleanup"] is False
            assert "TRANSPORT_UNCONFIRMED" in diagnostic["transport_events_before_cleanup"]
            assert "PROVIDER_UNCONFIRMED" in diagnostic["owner_events_before_cleanup"]
            assert diagnostic["root_cause"] == "UNDETERMINED"
            assert diagnostic["source_advance_samples"] == []
            assert diagnostic["native_stop_ack"] == "UNATTESTED"
            assert row["authorized_actions"] == row["learning_updates"] == 0
            assert row["text_current"] is False
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_wb_diagnostic_is_default_off():
    async def scenario():
        async with OneShotLocalModel() as server:
            observer = LiveL2Observer(
                model="self-demo-test-model", port=server.port, timeout_s=2,
                self_world_live=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            await asyncio.sleep(.12)
            row = await observer.close()
            assert "wb_s60_diagnostic" not in row
            assert row["wb_cognition_slice"] is False
            assert row["authorized_actions"] == 0
    asyncio.run(asyncio.wait_for(scenario(), 6))


@pytest.mark.parametrize("wb", [False, True])
@pytest.mark.parametrize("case,accepted", [
    ("valid_length", True), ("valid_chunked", True), ("503", False),
    ("malformed", False), ("alias", False), ("empty", False),
    ("reasoning_only", False), ("over_limit", False), ("unknown_metadata", False),
])
def test_wb_s60_synthetic_http_matrix_preserves_owner_contract(wb, case, accepted):
    from test_feature_s60b1_adapter import FakeHTTP, envelope, response

    async def scenario():
        value = envelope()
        value["model"] = "offline-model"
        value["choices"][0]["finish_reason"] = "length"
        value["usage"] = dict(prompt_tokens=1153, completion_tokens=96, total_tokens=1249)
        if case == "alias":
            value["model"] = "foreign-model"
        if case in {"empty", "reasoning_only"}:
            value["choices"][0]["message"]["content"] = ""
        if case == "reasoning_only":
            value["choices"][0]["message"]["reasoning_content"] = "synthetic reasoning"
        if case == "over_limit":
            value["usage"].update(completion_tokens=97, total_tokens=1250)
        if case == "unknown_metadata":
            value["unknown"] = True
        wire = response(
            b"{" if case == "malformed" else json.dumps(value).encode(),
            status=503 if case == "503" else 200, chunked=case == "valid_chunked",
        )
        async with FakeHTTP() as server:
            server.responses = [wire]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=wb,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            assert await server.next_post() == 0
            server.release[0].set()
            await asyncio.wait_for(observer._poll_task, 2)
            row = await observer.close()
            assert len(server.posts) == row["model_attempts"] == 1
            assert row["text_current"] is accepted
            assert row["status"] == (
                "ACCEPTED_READ_ONLY_SAME_PRESENT" if accepted else "UNCONFIRMED"
            )
            assert row["authorized_actions"] == row["learning_updates"] == 0
            assert row["backend_stop_ack"] is row["l0_blocked_on_l2"] is False
            if wb:
                diag = row["wb_s60_diagnostic"]
                assert diag["completion_state"] == (
                    "ACCEPTED_CURRENT" if accepted
                    else "PROVIDER_FAILED_HTTP_COMPLETION_UNCONFIRMED"
                )
                assert diag["lease_active_before_cleanup"] is not accepted
                assert diag["owner_completion_observed_before_cleanup"] is accepted
                assert diag["http_status"] == diag["completion_envelope"] == "UNRECORDED"
                assert diag["root_cause"] == "UNDETERMINED"
            else:
                assert "wb_s60_diagnostic" not in row
    asyncio.run(asyncio.wait_for(scenario(), 5))


@pytest.mark.parametrize("boundary", ["world_before", "world_after", "deadline", "cleanup"])
def test_wb_s60_completion_boundaries_keep_l0_independent(boundary):
    from test_feature_s60b1_adapter import FakeHTTP, envelope, response

    async def scenario():
        value = envelope()
        async with FakeHTTP() as server:
            server.responses = [response(json.dumps(value).encode())]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            assert await server.next_post() == 0
            # Real provider task held at a barrier, never an actual model call.
            ran = []
            await observer._owner.run_l0(lambda: _record_l0(ran))
            assert ran == [True]
            if boundary == "world_after":
                server.release[0].set()
                await asyncio.wait_for(observer._poll_task, 2)
                await observer.observe(scoped_world_probe(47))
            elif boundary == "world_before":
                await observer.observe(scoped_world_probe(47))
                await asyncio.wait_for(observer._poll_task, 2)
            elif boundary == "deadline":
                # Advance only S60's injected monotonic clock, no wall-clock sleep.
                observer._owner._clock = lambda: observer._started_at + 3
                observer._owner.tick()
                await asyncio.wait_for(observer._poll_task, 2)
            row = await observer.close()
            diag = row["wb_s60_diagnostic"]
            assert row["text_current"] is False
            assert len(server.posts) == 1
            assert row["authorized_actions"] == row["learning_updates"] == 0
            assert row["backend_stop_ack"] is row["l0_blocked_on_l2"] is False
            assert diag["accepted_text_ever_observed"] is (boundary == "world_after")
            if boundary == "world_after":
                assert diag["completion_state"] == "ACCEPTED_THEN_WORLD_ADVANCED"
            else:
                assert diag["http_completion_observed_before_cleanup"] is False
                assert "CLIENT_CANCEL_UNCONFIRMED" in diag["transport_events_after_cleanup"]
            if boundary == "cleanup":
                assert "CLIENT_CANCEL_UNCONFIRMED" not in diag["transport_events_before_cleanup"]
            if boundary == "world_before":
                sample = diag["source_advance_samples"][0]
                assert "HTTP_COMPLETION_OBSERVED" not in sample["provider_receipts_before"]
    asyncio.run(asyncio.wait_for(scenario(), 5))


async def _record_l0(ran):
    ran.append(True)


def test_wb_s60_http_completed_before_owner_poll_can_be_stale_rejected():
    from test_feature_s60b1_adapter import FakeHTTP, envelope, response

    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response(json.dumps(envelope()).encode())]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            await server.next_post()
            observer._poll_task.cancel()
            await asyncio.gather(observer._poll_task, return_exceptions=True)
            server.release[0].set()
            await asyncio.wait_for(observer._adapter._attempt.task, 2)
            # HTTP is fully validated, but owner has not polled its Future.
            await observer.observe(scoped_world_probe(47))
            assert observer._owner.tick() is None
            row = await observer.close()
            diag = row["wb_s60_diagnostic"]
            assert diag["completion_state"] == "HTTP_COMPLETED_S60_STALE_REJECTED"
            assert diag["owner_completion_observed_before_cleanup"] is True
            assert diag["accepted_text_ever_observed"] is False
            assert row["text_current"] is False
            assert row["authorized_actions"] == row["learning_updates"] == 0
    asyncio.run(asyncio.wait_for(scenario(), 5))


def test_wb_structured_l2_requires_explicit_opt_in_without_world(capsys):
    assert self_demo.main(["--wb-structured-l2"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "WB_JSON_L2_REQUIRES_WB_LIVE_L2"
    assert self_demo.main(["--wb-cognition-slice", "--wb-structured-l2"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "WB_JSON_L2_REQUIRES_WB_LIVE_L2"
    assert self_demo.main([
        "--wb-structured-l2", "--wb-cognition-slice", "--self-world-live",
        "--live-think",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "LIVE_L2_REQUIRES_NATIVE_WORLD"
    with pytest.raises(ValueError, match="explicit WB"):
        LiveL2Observer(model="test", port=12345, structured_json_off=True)
    with pytest.raises(ValueError, match="explicit WB"):
        LiveL2Observer(
            model="test", port=12345, self_world_live=True,
            wb_cognition_slice=True, structured_json_off="yes",
        )


@pytest.mark.parametrize("content,accepted", [
    ('{"uncertainty":"Which observed path is blocked?"}', True),
    ('{"uncertainty":""}', False),
    ('{"unknown":"x"}', False),
    ('{"uncertainty":"x","command":"MOVE_AWAY"}', False),
    ('not JSON', False),
])
def test_wb_structured_reasoning_off_bounded_json_advisory(content, accepted):
    from test_feature_s60b1_adapter import FakeHTTP, envelope, response

    async def scenario():
        wire = envelope()
        wire["choices"][0]["message"]["content"] = content
        async with FakeHTTP() as server:
            server.responses = [response(json.dumps(wire).encode())]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True,
                structured_json_off=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            assert await server.next_post() == 0
            sent = server.posts[0][1]
            assert sent["reasoning_effort"] == "none"
            assert sent["response_format"]["type"] == "json_schema"
            assert sent["response_format"]["json_schema"]["strict"] is True
            assert sent["response_format"]["json_schema"]["schema"][
                "additionalProperties"
            ] is False
            assert sent["max_tokens"] == 96
            server.release[0].set()
            await asyncio.wait_for(observer._poll_task, 2)
            row = await observer.close()
            assert row["structured_json_off"] is True
            assert row["text_current"] is accepted
            assert row["status"] == (
                "ACCEPTED_READ_ONLY_SAME_PRESENT" if accepted
                else "STRUCTURED_CONTENT_UNCONFIRMED"
            )
            if accepted:
                assert json.loads(row["text_observation_only"]) == {
                    "uncertainty": "Which observed path is blocked?",
                }
            else:
                assert row["text_observation_only"] is None
            assert row["authorized_actions"] == row["learning_updates"] == 0
            assert row["backend_stop_ack"] is row["gpu_release_verified"] is False
            assert row["l0_blocked_on_l2"] is False
            assert row["wb_s60_diagnostic"]["root_cause"] == "UNDETERMINED"
    asyncio.run(asyncio.wait_for(scenario(), 5))


@pytest.mark.parametrize("advance", [False, True])
def test_structured_wb_host_order_acceptance_before_or_after_native_advance(advance):
    """Synthetic received probes: never physical World or native Action proof."""
    from test_feature_s60b1_adapter import FakeHTTP, envelope, response

    async def scenario():
        wire = envelope()
        wire["choices"][0]["message"]["content"] = (
            '{"uncertainty":"Check whether the current target is visible."}'
        )
        async with FakeHTTP() as server:
            server.responses = [response(json.dumps(wire).encode())]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True, structured_json_off=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            assert await server.next_post() == 0
            server.release[0].set()
            await asyncio.wait_for(observer._poll_task, 2)
            if advance:
                await observer.observe(scoped_world_probe(47))
            live_view = observer.read_wb_l2_uncertainty()
            assert live_view.state == (
                "PAST_EPOCH_REVIEW_ONLY" if advance else "CURRENT_EPOCH_READ_ONLY"
            )
            assert live_view.current_uncertainty == (
                None if advance else "Check whether the current target is visible."
            )
            assert live_view.past_review_candidate == (
                "Check whether the current target is visible." if advance else None
            )
            shadow = observer.read_wb_l1_attention_shadow()
            ab = observer.read_wb_l1_attention_ab()
            review = observer.read_wb_past_review_handoff()
            if advance:
                assert ab.state == "UNAVAILABLE"
            else:
                assert ab.state == "SHADOW_SELECTION_DIFFERENCE"
                assert ab.observed_candidate_count == 1
                assert ab.baseline_selected == ("wb-native-observed-0",)
                assert ab.with_l2_selected == ("wb-l2-uncertainty",)
                assert ab.selection_changed is True
                assert ab.actual_l1_policy_changed is False
                assert ab.useful_for_goal is False
            assert shadow.state == (
                "UNAVAILABLE" if advance else "ATT_SELECTED_READ_ONLY"
            )
            assert review.state == (
                "PENDING_INDEPENDENT_OUTCOME" if advance else "UNAVAILABLE"
            )
            if advance:
                assert review.origin_world_seq == 19
                assert review.later_world_seq == 47
                assert review.outcome_verified is False
                assert review.learning_authorized is False
            row = await observer.close()
            assert row["wb_l2_readonly_at_close"] == live_view.to_mapping()
            assert row["wb_l1_attention_at_admission"]["state"] == (
                "ATT_SELECTED_READ_ONLY"
            )
            assert row["wb_l1_attention_ab_at_admission"]["state"] == (
                "SHADOW_SELECTION_DIFFERENCE"
            )
            assert row["wb_l1_attention_ab_at_admission"]["selection_changed"] is True
            assert row["wb_l1_attention_ab_at_close"] == ab.to_mapping()
            assert row["wb_l1_attention_at_close"] == shadow.to_mapping()
            assert row["wb_l2_past_review_at_close"] == review.to_mapping()
            assert observer.read_wb_l2_uncertainty().state == "UNAVAILABLE"
            assert observer.read_wb_l1_attention_shadow().state == "UNAVAILABLE"
            assert observer.read_wb_past_review_handoff().state == "UNAVAILABLE"
            host = row["wb_structured_acceptance_host_order"]
            assert host == {
                "source_world_seq": 19,
                "latest_native_seq_at_acceptance": 19,
                "native_callbacks_seen_at_acceptance": 2,
                "observer_closed_at_acceptance": False,
                "owner_completion_observed_at_acceptance": True,
            }
            assert row["source_world_seq"] == 19
            assert row["latest_world_seq"] == (47 if advance else 19)
            assert row["text_current"] is not advance
            assert row["status"] == (
                "EXPIRED_WORLD_ADVANCED" if advance
                else "ACCEPTED_READ_ONLY_SAME_PRESENT"
            )
            assert row["wb_s60_diagnostic"]["completion_state"] == (
                "ACCEPTED_THEN_WORLD_ADVANCED" if advance else "ACCEPTED_CURRENT"
            )
            assert row["authorized_actions"] == row["learning_updates"] == 0
            assert row["l0_blocked_on_l2"] is False
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_structured_wb_no_host_acceptance_from_http_failure():
    from test_feature_s60b1_adapter import FakeHTTP, response

    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response(status=503)]
            observer = LiveL2Observer(
                model="offline-model", port=server.port, timeout_s=2,
                self_world_live=True, wb_cognition_slice=True, structured_json_off=True,
            )
            await observer.observe(scoped_world_probe(8))
            await observer.observe(scoped_world_probe(19))
            assert await server.next_post() == 0
            server.release[0].set()
            await asyncio.wait_for(observer._poll_task, 2)
            assert observer.read_wb_l2_uncertainty().state == "UNAVAILABLE"
            row = await observer.close()
            assert row["wb_structured_acceptance_host_order"] is None
            assert row["wb_l2_readonly_at_close"]["state"] == "UNAVAILABLE"
            assert row["wb_l1_attention_at_admission"] is None
            assert row["wb_l1_attention_ab_at_admission"] is None
            assert row["wb_l1_attention_ab_at_close"]["state"] == "UNAVAILABLE"
            assert row["wb_l1_attention_at_close"]["state"] == "UNAVAILABLE"
            assert row["wb_l2_past_review_at_close"]["state"] == "UNAVAILABLE"
            assert row["text_current"] is False
            assert row["status"] == "UNCONFIRMED"
            assert row["authorized_actions"] == row["learning_updates"] == 0
    asyncio.run(asyncio.wait_for(scenario(), 6))


def test_wb_optional_callback_failure_cannot_veto_original_s49_l0(
    monkeypatch, tmp_path,
):
    """Synthetic owner stub; no Minecraft, Gemma or provider transport."""
    import adapters.mineflayer.s49_normal_session_real_ci as s49

    called = []

    async def fake_original_s49(report_path, log_path, *, live_probe=None):
        assert live_probe is not None
        for seq in (8, 19):
            await live_probe(scoped_world_probe(seq))
            called.append(seq)
        return 0

    async def broken_optional_observer(self, reading):
        raise RuntimeError("synthetic WB projection callback failure")

    monkeypatch.setattr(s49, "qualify", fake_original_s49)
    monkeypatch.setattr(LiveL2Observer, "observe", broken_optional_observer)
    result = asyncio.run(self_demo._run_disposable(
        tmp_path / "unused-native-report.json",
        tmp_path / "unused-model-log.json",
        live_model=("offline-model", 12345, 1),
        self_world_live=True, wb_cognition_slice=True,
        structured_json_off=True,
    ))
    assert result == 0
    assert called == [8, 19]
    row = json.loads((tmp_path / "live_l2.jsonl").read_text().strip())
    assert row["status"] == "SOURCE_CALLBACK_UNCONFIRMED"
    assert row["source_callback_failure"] == "RuntimeError"
    assert row["wb_l2_readonly_at_close"]["state"] == "UNAVAILABLE"
    assert row["wb_l1_attention_at_admission"] is None
    assert row["wb_l1_attention_ab_at_admission"] is None
    assert row["wb_l1_attention_ab_at_close"]["state"] == "UNAVAILABLE"
    assert row["wb_l1_attention_at_close"]["state"] == "UNAVAILABLE"
    assert row["wb_l2_past_review_at_close"]["state"] == "UNAVAILABLE"
    assert row["wb_structured_acceptance_host_order"] is None
    assert row["model_attempts"] == row["authorized_actions"] == 0
    assert row["learning_updates"] == 0
    assert row["l0_blocked_on_l2"] is False
