"""M0.2 Paper DEV source controls; no Minecraft/Java/network in these tests."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.m02_paper_dev import s51_paper_physics_dev as dev
from adapters.mineflayer.m02_paper_dev import s51_paper_qualification as q
from adapters.mineflayer.m02_paper_dev import v7_paired_config as v7
from adapters.mineflayer.m02_paper_dev.native_l0 import PaperL0Rejected, PaperNativeL0
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import (
    M02_CONFIRM,
    PAPER_PREWORLD_ASSET_PINS,
    PAPER_PREWORLD_PROFILE,
    M02DevRejected,
    _fresh_asset,
    _port_free,
    _read_world_receipts,
    _sha256,
    main,
    qualification_asset_preflight,
    run,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerInventoryItem,
    MineflayerPosition,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor


def test_hash_asset_requires_original_bytes(tmp_path):
    path = tmp_path / "paper-test.jar"
    path.write_bytes(b"paper-dev-just-test-bytes")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert _fresh_asset(path, sha) == path
    assert _sha256(path) == sha
    with pytest.raises(M02DevRejected, match="SHA256 mismatch"):
        _fresh_asset(path, "0" * 64)
    link = tmp_path / "symlink.jar"
    link.symlink_to(path)
    with pytest.raises(M02DevRejected, match="absolute unlinked"):
        _fresh_asset(link, sha)


def test_original_event_log_must_prove_walk_basal_and_plugin(tmp_path):
    log = tmp_path / "server.log"
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20 player=RelaySelf food=20 saturation=5 exhaustion=0.02\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.006 "
        "cumulative_blocks=0.6 cumulative_billed=0.006\n",
        encoding="utf-8",
    )
    report = _read_world_receipts(log)
    assert report["count_walk_native_events"] == 1
    assert report["count_walk_motion_packets"] == 1
    assert report["world_measured_walk_blocks"] == pytest.approx(0.6)
    assert report["world_billed_walk_exhaustion"] == pytest.approx(0.006)
    assert report["native_event_identity_independently_qualified"] is False
    log.write_text("M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n")
    with pytest.raises(M02DevRejected, match="startup/basal/WALK"):
        _read_world_receipts(log)
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=1.0E-4\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.006\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="replaced by zero"):
        _read_world_receipts(log)
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.001\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="differs from measured path"):
        _read_world_receipts(log)


def test_absent_confirmation_prevents_java_and_creation(tmp_path):
    out = tmp_path / "new-world"
    rc = asyncio.run(run(
        out, tmp_path / "absent.jar", "0" * 64,
        tmp_path / "absent-plugin.jar", "1" * 64,
        confirmation="NOT_AUTHORIZED",
    ))
    assert rc == 2
    assert not out.exists()


def test_confirmation_is_typed_and_not_default():
    assert M02_CONFIRM == "M02-DEV-I-OWN-DISPOSABLE-PAPER-WORLD"
    assert callable(_port_free)


def _synthetic_preworld_assets(root, monkeypatch):
    import adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev as s
    root.mkdir()
    content = {
        "paper-1.21.8.jar": b"fixture-paper-jar",
        "relay-metabolism-paper-dev.jar": b"fixture-plugin-jar",
        "config.yml": b"dev-enabled: true\ntarget-player: RelaySelf\n",
        "server.properties": b"online-mode=false\ngamemode=survival\n",
    }
    hashes = {}
    for name, data in content.items():
        (root / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(s, "PAPER_PREWORLD_ASSET_PINS", hashes)
    return hashes


def test_qualification_asset_preworld_read_only_with_honest_ceiling(tmp_path, monkeypatch, capsys):
    root = tmp_path / "new-only-four-assets"
    digests = _synthetic_preworld_assets(root, monkeypatch)
    result = qualification_asset_preflight(root)
    assert result["preworld_profile"] == PAPER_PREWORLD_PROFILE
    assert result["verified_assets_sha256"] == digests
    assert result["new_paper_world"] == "NOT_CREATED"
    assert result["new_world_snapshot_seed"] == "NOT_BOUND"
    assert result["physical_world_launches"] == 0
    assert result["qualified"] is False
    assert not result["science_go"] and not result["production_go"]
    assert main(["--qualification-preflight", "--asset-root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["qualified"] is False
    assert set(p.name for p in root.iterdir()) == set(digests)


def test_qualification_preworld_rejects_tamper_extra_symlink_and_unpinned(tmp_path, monkeypatch):
    root = tmp_path / "four"
    _synthetic_preworld_assets(root, monkeypatch)
    (root / "extra").write_bytes(b"not included")
    with pytest.raises(M02DevRejected, match="exact four"):
        qualification_asset_preflight(root)
    (root / "extra").unlink()
    plugin = root / "relay-metabolism-paper-dev.jar"
    plugin.write_bytes(b"modified")
    with pytest.raises(M02DevRejected, match="non-pinned"):
        qualification_asset_preflight(root)
    plugin.unlink()
    plugin.symlink_to(root / "paper-1.21.8.jar")
    with pytest.raises(M02DevRejected, match="unsafe"):
        qualification_asset_preflight(root)
    plugin.unlink()
    # An unpinned brand-new directory never authorizes a Java start.
    assert main(["--qualification-preflight", "--asset-root", str(root)]) == 2


def test_qualification_preflight_and_dev_cli_never_mix(tmp_path):
    with pytest.raises(SystemExit):
        main(["--qualification-preflight", "--asset-root", str(tmp_path),
              "--confirm", M02_CONFIRM])
    with pytest.raises(SystemExit):
        main(["--asset-root", str(tmp_path)])
    assert len(PAPER_PREWORLD_ASSET_PINS) == 4


def _assets(tmp_path, monkeypatch):
    root = tmp_path / "assets"
    root.mkdir()
    d = {
        "paper-1.21.8.jar": b"paper fake binary offline",
        "relay-metabolism-paper-dev.jar": b"plugin fake binary offline",
        "config.yml": b"dev-enabled: true\ntarget-player: RelaySelf\n",
        "server.properties": (
            b"server-ip=127.0.0.1\nonline-mode=false\ngamemode=survival\n"),
    }
    for name, value in d.items():
        (root / name).write_bytes(value)
    monkeypatch.setattr(dev, "PAPER_PREWORLD_ASSET_PINS", {
        k: hashlib.sha256(v).hexdigest() for k, v in d.items()})
    monkeypatch.setattr(q, "ASSET_NAMES", frozenset(d))
    return root


def test_user_grant_has_nondev_authorized_source():
    supervisor = ActionSupervisor()
    issued = q._issue(supervisor, "m02-action-once", "eat",
                      "m02-intent", "controlled qualification", time_base=30)
    assert issued.state is ActionState.ISSUED
    assert q.GRANT != dev.M02_CONFIRM
    assert "QUALIFICATION" in q.GRANT


def test_four_assets_fail_closed_and_do_not_launch_world(tmp_path, monkeypatch):
    root = _assets(tmp_path, monkeypatch)
    assert q.check_assets(root) == dev.PAPER_PREWORLD_ASSET_PINS
    for p in root.iterdir():
        before = p.read_bytes()
        if p.name == "paper-1.21.8.jar":
            p.write_bytes(before + b"mutated")
            with pytest.raises(q.QualificationBlocked):
                q.check_assets(root)
            p.write_bytes(before)


def test_symlink_or_unsafe_output_cannot_start(tmp_path, monkeypatch):
    root = _assets(tmp_path, monkeypatch)
    actual = root / "server.properties"
    original = actual.read_bytes()
    actual.unlink()
    actual.symlink_to(root / "config.yml")
    with pytest.raises(q.QualificationBlocked):
        q.check_assets(root)
    actual.unlink()
    actual.write_bytes(original)

    async def forbidden(*_args, **_kw):
        pytest.fail("physical Java started in offline test")
    monkeypatch.setattr(q, "_ready_server", forbidden)
    monkeypatch.setattr(
        q, "_java21_runtime",
        lambda: {"java_executable": "/synthetic/java21", "java_major": "21"},
    )
    with pytest.raises(q.QualificationBlocked, match="confirmation"):
        asyncio.run(q.run(
            asset_root=root, output_root=tmp_path / "never",
            confirm="UNAUTHORIZED"))
    assert not (tmp_path / "never").exists()
    with pytest.raises(q.QualificationBlocked, match="existing World"):
        (tmp_path / "taken").mkdir()
        asyncio.run(q.run(
            asset_root=root, output_root=tmp_path / "taken",
            confirm=q.CONFIRM))


def test_native_stop_must_match_single_session_and_seq(tmp_path):
    path = tmp_path / "source.jsonl"
    import json
    lines = [
        {"type": "observation", "session_id": "a", "seq": i}
        for i in range(10)
    ]
    lines[8]["type"] = "shutdown_ack"
    lines[9]["type"] = "connection_end"
    path.write_text("".join(json.dumps(x)+"\n" for x in lines))
    assert q._terminal_native(path, "a")["native_stop_ack_seq"] == 8
    lines[7]["session_id"] = "other"
    path.write_text("".join(json.dumps(x)+"\n" for x in lines))
    with pytest.raises(q.QualificationBlocked):
        q._terminal_native(path, "a")


def test_qualification_wrong_java_prelaunch_does_not_consume(tmp_path, monkeypatch):
    from types import SimpleNamespace

    root = _assets(tmp_path, monkeypatch)
    monkeypatch.setattr(q.shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(q.subprocess, "run", lambda *_a, **_k:
                        SimpleNamespace(returncode=0, stdout="",
                                        stderr='openjdk version "17.0.16"'))
    with pytest.raises(q.QualificationBlocked, match="Java 21"):
        asyncio.run(q.run(asset_root=root, output_root=tmp_path / "never",
                          confirm=q.CONFIRM))
    assert not (tmp_path / "never").exists()
    monkeypatch.setattr(q.subprocess, "run", lambda *_a, **_k:
                        SimpleNamespace(returncode=0, stdout="",
                                        stderr='openjdk version "21.0.9"'))
    assert q._java21_runtime()["java_major"] == "21"


def test_initial_world_level_original_is_saved_before_action(tmp_path, monkeypatch):
    original = b"level-dat-original-from-controlled-synthetic-world"
    world = tmp_path / "disposable-world"
    source_dir = world / "s31a-ephemeral"
    source_dir.mkdir(parents=True)
    (source_dir / "level.dat").write_bytes(original)
    output_dir = tmp_path / "evidence"
    output_dir.mkdir()
    issued = []

    class StubStdin:
        async def drain(self):
            pass

    class StubServer:
        returncode = None
        stdin = StubStdin()

    monkeypatch.setattr(dev, "_command", lambda _server, cmd: issued.append(cmd))
    result = asyncio.run(dev._save_and_capture_initial_world(
        StubServer(), world, output_dir))
    assert issued == ["save-all flush"]
    assert result["source_world_path"] == "s31a-ephemeral/level.dat"
    assert result["size_bytes"] == len(original)
    assert result["sha256"] == hashlib.sha256(original).hexdigest()
    assert (output_dir / "initial_world_level.dat").read_bytes() == original
    assert result["snapshot_phase"] == "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION"
    with pytest.raises(dev.M02DevRejected, match="pre-Action World snapshot"):
        asyncio.run(dev._save_and_capture_initial_world(
            StubServer(), world, output_dir))


def test_paper_native_l0_hunger_without_virtual_body():
    first = s46.case()
    eaten = replace(first, snapshot=replace(first.snapshot, inventory=(
        MineflayerInventoryItem("cooked_beef", 3, 4),
    )))
    l0 = PaperNativeL0(eaten.session_id)
    wait = replace(eaten, snapshot=replace(eaten.snapshot, food=20.0))
    result = l0.decide(wait)
    assert result.kind == "WAIT"
    assert result.eat_choice is None and result.ground_target is None
    hungry = replace(eaten, seq=eaten.seq + 1, request_id="paper-next-native")
    selection = l0.decide(hungry)
    assert selection.kind == "EAT"
    assert selection.eat_choice.item_name == "cooked_beef"
    assert selection.probe_seq == hungry.seq
    assert not hasattr(l0, "body") and not hasattr(l0, "credit_count")
    with pytest.raises(Exception):
        l0.decide(hungry)
    with pytest.raises(PaperL0Rejected):
        l0.decide(replace(hungry, seq=hungry.seq + 1, session_id="other"))


def test_paper_l0_single_ground_seek_is_candidate_not_known_food():
    p = s46.case()
    pos = p.snapshot.position
    item = MineflayerEntityFact(
        123, "item", "other", 2.5,
        MineflayerPosition(pos.x + 2.5, pos.y, pos.z),
    )
    source = replace(p, snapshot=replace(
        p.snapshot, inventory=(),
        nearby_entities=(item,),
        nearby_entities_coverage=replace(
            p.snapshot.nearby_entities_coverage, candidate_count=1,
            truncated=False,
        ),
    ))
    l0 = PaperNativeL0(source.session_id)
    candidate = l0.decide(source)
    assert candidate.kind == "SEEK" and candidate.ground_target.entity_id == 123
    assert candidate.eat_choice is None
    assert candidate.ground_target.waypoint().max_step_m == 1.0
    fed = replace(source, seq=source.seq + 1,
                  request_id="paper-fed", snapshot=replace(source.snapshot, food=20))
    assert l0.decide(fed).kind == "WAIT"


def test_paper_l0_ambiguous_or_truncated_target_fails_safe():
    import test_b0_ground_foraging as ground
    source = ground._ground()
    original = source.snapshot.nearby_entities[0]
    ambiguous = replace(source, snapshot=replace(
        source.snapshot, nearby_entities=(original, original),
        nearby_entities_coverage=replace(
            source.snapshot.nearby_entities_coverage, candidate_count=2,
        ),
    ))
    assert PaperNativeL0(source.session_id).decide(ambiguous).kind == "WAIT"
    # Adapter-valid truncated source: 16 displayed out of 17 candidates.
    truncated = replace(source, snapshot=replace(
        source.snapshot,
        nearby_entities=(original,) * 16,
        nearby_entities_coverage=replace(
            source.snapshot.nearby_entities_coverage,
            candidate_count=17, truncated=True,
        ),
    ))
    assert PaperNativeL0(source.session_id).decide(truncated).kind == "WAIT"


def test_paper_pickup_contrast_uses_real_beef_delta_not_unknown_entity_contents():
    import test_b0_ground_foraging as ground
    from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
        PaperForageRejected,
        paper_pickup_contrast,
    )
    source = ground._ground()
    target = ground.select_ground_target(source)
    after = replace(
        source, seq=source.seq + 5, request_id="paper-picked-beef",
        snapshot=replace(
            source.snapshot, inventory=(MineflayerInventoryItem("cooked_beef", 1, 4),),
            nearby_entities=(),
            nearby_entities_coverage=replace(
                source.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ),
    )
    match = paper_pickup_contrast(source, after, target)
    assert match["cooked_beef_inventory_delta"] == 1
    assert match["strict_player_collect_causality"] == "UNKNOWN"
    assert match["item_content_from_native_entity_metadata"] == "UNKNOWN"
    with pytest.raises(PaperForageRejected):
        paper_pickup_contrast(source, replace(after, session_id="foreign"), target)
    with pytest.raises(PaperForageRejected):
        paper_pickup_contrast(
            source, replace(after, snapshot=replace(
                after.snapshot, inventory=(MineflayerInventoryItem("rotten_flesh", 1, 4),),
            )), target,
        )
    with pytest.raises(PaperForageRejected):
        paper_pickup_contrast(
            source, replace(after, snapshot=replace(
                after.snapshot, nearby_entities=source.snapshot.nearby_entities,
                nearby_entities_coverage=source.snapshot.nearby_entities_coverage,
            )), target,
        )


def test_paper_foraging_requires_fresh_trace_before_owning_world():
    from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
        PaperForageRejected,
        paper_ground_forage,
    )
    trace = {"old": "foreign"}
    with pytest.raises(PaperForageRejected):
        asyncio.run(paper_ground_forage(
            None, None, issuer=None, provenance=None, trace=trace,
        ))
    assert trace == {"old": "foreign"}


def test_paper_multistep_foraging_accepts_no_native_walk_callbacks_only_when_packets_prove_charge(
    tmp_path,
):
    from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _read_world_receipts

    log = tmp_path / "paper.log"
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20 player=RelaySelf exhaustion=0.02\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=1.1 billed=0.011\n"
        "M02_DEV_MOTION id=2 reason=WALK blocks=1.05 billed=0.0105\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="packet motion"):
        _read_world_receipts(log)
    result = _read_world_receipts(
        log, max_path_blocks=16, allow_packet_only_walk=True,
    )
    assert result["count_walk_native_events"] == 0
    assert result["walk_native_callbacks_present"] is False
    assert result["physical_walk_billing_source"] == "PLAYER_MOVE_EVENT_COORDINATE_PATH"
    assert result["world_measured_walk_blocks"] == pytest.approx(2.15)
    assert result["world_billed_walk_exhaustion"] == pytest.approx(0.0215)
    # Absence of *both* the native callbacks and true movement is not a PASS.
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20 player=RelaySelf exhaustion=0.02\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="packet motion"):
        _read_world_receipts(log, max_path_blocks=16, allow_packet_only_walk=True)
    # Billed amount must still equal actual moved distance, not issued intent.
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20 player=RelaySelf exhaustion=0.02\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=2.15 billed=0.001\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="charge differs"):
        _read_world_receipts(log, max_path_blocks=16, allow_packet_only_walk=True)


def test_paper_b1_requires_explicit_forage_and_does_not_reuse_any_grant(tmp_path):
    with pytest.raises(SystemExit):
        main(["--paper-b1", "on"])
    with pytest.raises(SystemExit):
        main(["--qualification-preflight", "--paper-b1", "off",
              "--asset-root", str(tmp_path)])
    assert dev.M02_CONFIRM == M02_CONFIRM


def test_paper_b1_foraging_fail_closed_on_bad_switch_or_dirty_trace():
    from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
        PaperForageRejected,
        paper_ground_forage,
    )
    for retention in ("on", 1):
        with pytest.raises(PaperForageRejected):
            asyncio.run(paper_ground_forage(
                None, None, issuer=None, provenance=None,
                trace={}, b1_retention=retention,
            ))
    with pytest.raises(PaperForageRejected):
        asyncio.run(paper_ground_forage(
            None, None, issuer=None, provenance=None,
            trace={"frozen": True}, b1_retention=True,
        ))


def test_paper_b1_uses_original_retained_source_and_cheap_off_policy():
    import test_b1_local_adaptation as b1
    from adapters.mineflayer.b1_local_adaptation import B1LocalCandidate

    before, blocked, followup, target = b1.source()
    for retention, direction in ((True, -1), (False, 1)):
        agent = B1LocalCandidate(before.session_id, retain=retention)
        agent.record_blocked(before, blocked, followup, target)
        fresh = replace(followup, seq=followup.seq + 1,
                        request_id="paper-fresh-after-blocked")
        chosen = agent.next_waypoint(fresh, target)
        assert chosen.goal_id == "b1-local-lateral"
        assert (chosen.target.z - followup.snapshot.position.z) * direction > 0
        assert agent.evidence()["retained_observations"] == int(retention)
        assert agent.evidence()["reused_for_lateral_choice"] == int(retention)
        assert agent.evidence()["lateral_choice_count"] == 1
        assert not agent.evidence()["habit_created"]


def test_v7_offline_5_arm_candidate_configs_preserve_qualified_baseline(tmp_path):
    raw = v7.TEMPLATE.read_bytes()
    configs = {arm: v7.render_arm(raw, arm) for arm in v7.ARMS}
    assert len(configs) == 5
    assert configs["BASE_ON"] == configs["SHAM_ON"]
    assert v7.sha256(configs["BASE_ON"]) == v7.BASELINE_ENABLED_SHA256
    assert len(set(map(v7.sha256, configs.values()))) == 4
    assert b"WALK: {unit: block, standard: 0.01, multiplier: 0.0" in configs["WALK_ZERO"]
    assert b"BASAL: {unit: tick, standard: 0.001, multiplier: 0.0" in configs["BASAL_ZERO"]
    for data in configs.values():
        assert b"COGNITION: {unit: work, standard: 0.0, multiplier: 1.0" in data
        assert b"dev-enabled: true" in data
    target = tmp_path / "candidate-only"
    receipt = v7.stage_candidate_configs(raw, target)
    assert receipt["real_world_starts"] == 0
    assert receipt["classification"] == "S_V7_M02_FIVE_CANDIDATE_CONFIGS_OFFLINE_ONLY"
    assert not receipt["science_go"] and not receipt["qualification_reused"]
    for arm, data in configs.items():
        assert (target / arm / "config.yml").read_bytes() == data
    assert set(p.name for p in target.iterdir()) == set(configs) | {"offline-only-manifest.json"}
    with pytest.raises(v7.V7ProfileRejected):
        v7.stage_candidate_configs(raw, target)


def test_v7_reject_changed_baseline_unknown_arm_and_unsafe_destination(tmp_path):
    raw = v7.TEMPLATE.read_bytes()
    with pytest.raises(v7.V7ProfileRejected):
        v7.render_arm(raw.replace(b"standard: 0.01", b"standard: 0.02"), "BASE_ON")
    with pytest.raises(v7.V7ProfileRejected):
        v7.render_arm(raw, "UNREGISTERED")
    with pytest.raises(v7.V7ProfileRejected):
        v7.stage_candidate_configs(raw, Path("relative-candidate-dir"))
    assert not (tmp_path / "not-absolute").exists()


def test_paper_b1_memory_original_is_immediate_append_only(tmp_path):
    from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
        PaperForageRejected,
        append_b1_original,
    )
    root = tmp_path / "original-b1.jsonl"
    with root.open("xb") as stream:
        first = {
            "event": "BLOCKED_MEMORY_RETAINED", "session_id": "src",
            "blocked_action_id": "S50-1", "memory": {
                "memory_id": "m", "content": '{"effect_kind":"BLOCKED"}',
            },
        }
        append_b1_original(stream, first)
        saved = root.read_bytes()
        assert len(saved.splitlines()) == 1
        second = {
            "event": "LATERAL_ACTION_ISSUED", "session_id": "src",
            "action_id": "S50-2", "source_probe_seq": 44,
            "memory_content_sha256": hashlib.sha256(
                first["memory"]["content"].encode("utf-8"),
            ).hexdigest(),
        }
        append_b1_original(stream, second)
    rows = [json.loads(x) for x in root.read_text().splitlines()]
    assert rows == [first, second]
    assert root.read_bytes().startswith(saved)
    with pytest.raises(PaperForageRejected):
        with root.open("ab") as stream:
            append_b1_original(stream, {
                "event": "RETROSPECTIVE_MEMORY_FABRICATION",
            })


def test_paper_b1_missing_memory_stream_fails_before_world_use():
    from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
        PaperForageRejected,
        paper_ground_forage,
    )
    with pytest.raises(PaperForageRejected, match="source|switch|fresh"):
        asyncio.run(paper_ground_forage(
            None, None, issuer=None, provenance=None,
            trace={}, b1_retention=True, b1_memory_original=None,
        ))


def test_v7_physical_paper_log_synthetic_rates_and_real_player_tick_gate(tmp_path):
    body = (
        "M02_DEV_BODY sampled_tick=1 player=RelaySelf food=20 saturation=5"
        " health=20 exhaustion=0.001 motion_blocks=0.0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=1.25 billed=0.0125"
        " cumulative_blocks=1.25 cumulative_billed=0.0125\n"
        "M02_DEV_BODY sampled_tick=200 player=RelaySelf food=20 saturation=5"
        " health=20 exhaustion=0.20 motion_blocks=1.25\n"
    )
    log = tmp_path / "paper_server.log"
    log.write_text(body, encoding="utf-8")
    result = asyncio.run(dev._v7_wait_source_tick(log, "BASE_ON"))
    assert result["last_sampled_player_tick"] == 200
    assert result["observed_motion_packets"] == 1
    assert result["observed_motion_path_blocks"] == pytest.approx(1.25)
    assert result["observed_motion_debit"] == pytest.approx(0.0125)
    assert not result["science_go"]
    assert result["basal_source_charge_inferred_not_independently_attested"]

    log.write_text(body.replace("billed=0.0125", "billed=0.0"))
    off = asyncio.run(dev._v7_wait_source_tick(log, "WALK_ZERO"))
    assert off["observed_motion_debit"] == 0.0
    with pytest.raises(dev.M02DevRejected, match="charge"):
        asyncio.run(dev._v7_wait_source_tick(log, "BASE_ON"))
    with pytest.raises(dev.M02DevRejected, match="unregistered"):
        asyncio.run(dev._v7_wait_source_tick(log, "UNKNOWN"))


def test_v7_original_tick_source_missing_does_not_convert_walltime(tmp_path, monkeypatch):
    log = tmp_path / "paper_server.log"
    log.write_text("M02_DEV_BODY sampled_tick=1 exhaustion=0.0 motion_blocks=0.0\n")
    async def no_wait(_seconds):
        raise dev.M02DevRejected("no native World tick 200 after real bounded wait")
    monkeypatch.setattr(dev.asyncio, "sleep", no_wait)
    with pytest.raises(dev.M02DevRejected, match="native World tick"):
        asyncio.run(dev._v7_wait_source_tick(log, "BASAL_ZERO"))
