"""W4 TEST-only geometry and isolated ledger attacks; no external trust."""
from __future__ import annotations

import json
import math
import shutil
import sqlite3
from dataclasses import replace

import pytest

import test_self_world_stage_s_feedback as sf
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerPosition,
    mineflayer_yaw_to_target,
    parse_mineflayer_line,
)
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
    W4SyntheticOrientation,
    external_trust_readout,
    plan_native_nh1_placement,
    plan_synthetic_nh1_placement,
    require_native_nh1_orientation,
)
from adapters.mineflayer.self_world_stage_w_gate import (
    StageWGateRejected,
    StageWPersistentGrantLedger,
)

pytest_plugins = ("test_self_world_stage_w_gate",)


def orientation():
    return W4SyntheticOrientation("synthetic-only", 5, MineflayerPosition(0, 64, 0), 0, 0)


@pytest.mark.parametrize("yaw", (0, math.pi/2, math.pi, -math.pi/2, 0.723))
@pytest.mark.parametrize("slot", (0, 1, 2))
def test_geometry(yaw, slot):
    o = replace(orientation(), yaw_rad=yaw, pitch_rad=0.4)
    result = plan_synthetic_nh1_placement(o, expected_session=o.session_id, before_seq=6, slot=slot)
    assert math.dist((o.position.x, o.position.z), (result.spawn.x, result.spawn.z)) == pytest.approx(10 if slot == 0 else 2)
    assert result.spawn.y == o.position.y
    if slot:
        actual = mineflayer_yaw_to_target(o.position, result.spawn)
        assert math.sin(actual) == pytest.approx(math.sin(yaw))
        assert math.cos(actual) == pytest.approx(math.cos(yaw))
    else:
        assert result.spawn == MineflayerPosition(10, 64, 0)
    assert result.command.startswith("summon minecraft:zombie ")
    assert not result.physical_run_permitted and not result.source_orientation_qualified
    assert result.source_probe_request_id is None
    assert result.source_reference is None


@pytest.mark.parametrize("case", ("absent", "foreign", "replayed", "nan", "pitch", "slot"))
def test_missing_or_wrong_source_blocks(case):
    o = orientation()
    kwargs = dict(expected_session=o.session_id, before_seq=6, slot=1)
    if case == "absent":
        o = None
    elif case == "foreign":
        kwargs["expected_session"] = "other"
    elif case == "replayed":
        kwargs["before_seq"] = 5
    elif case == "nan":
        o = replace(o, yaw_rad=math.nan)
    elif case == "pitch":
        o = replace(o, pitch_rad=2)
    else:
        kwargs["slot"] = 3
    with pytest.raises(W4PreworldBlocked):
        plan_synthetic_nh1_placement(o, **kwargs)


def test_current_native_source_and_external_trust_never_enable_live():
    witness = sf._synthetic_targeted_witness()
    with pytest.raises(W4PreworldBlocked, match="source-bound yaw/pitch"):
        require_native_nh1_orientation(witness.original_probe)
    assert external_trust_readout()["classification"] == "W4_EXTERNAL_TRUST_NO_GO"


@pytest.mark.parametrize("delta", (0.099, 0.100, 0.101, -0.099, -0.100, -0.101))
def test_unchanged_exact_stage_s_boundaries(delta):
    witness = sf._synthetic_targeted_witness(-delta, 0)
    result = sf.assess_stage_s_original_separation(witness, sf.StageSPredeclaredSeparationRule())
    # Compare the actual binary native distance subtraction, without rounding.
    actual = result.distance_after_m - result.distance_before_m
    expected = "INCREASE" if actual >= .100 else "DECREASE" if actual <= -.100 else "HOLD"
    assert result.direction.value.upper() == expected
    assert not result.s10_committed


def reserve(ledger, sample):
    ledger.reserve_once(sample["request"], issuer_fingerprint="TEST", archive_sha256=sample["archive_sha"])


@pytest.mark.parametrize("attack", ("symlink", "parent_symlink", "replacement", "hardlink", "mode", "missing"))
def test_ledger_path_attack_rejected(sample, tmp_path, attack):
    path = tmp_path / "spent.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    if attack == "parent_symlink":
        link = tmp_path / "alias"
        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(StageWGateRejected):
            StageWPersistentGrantLedger(link / path.name)
        return
    if attack == "mode":
        path.chmod(0o644)
    elif attack == "hardlink":
        (tmp_path / "hard").hardlink_to(path)
    else:
        saved = tmp_path / "saved.sqlite3"
        path.rename(saved)
        if attack == "symlink":
            path.symlink_to(saved)
        elif attack == "replacement":
            shutil.copyfile(saved, path)
            path.chmod(0o600)
    with pytest.raises(StageWGateRejected):
        reserve(ledger, sample)


def test_locked_ledger_denies_and_leaves_no_spend(sample, tmp_path):
    path = tmp_path / "locked.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(StageWGateRejected):
            reserve(ledger, sample)
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)


def test_disposable_rollback_clone_demonstrates_global_single_use_gap(sample, tmp_path):
    path = tmp_path / "original.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    clone = tmp_path / "clone.sqlite3"
    shutil.copy2(path, clone)  # Only a disposable TEST ledger, never historical evidence.
    reserve(ledger, sample)
    with pytest.raises(StageWGateRejected):
        reserve(ledger, sample)
    reserve(StageWPersistentGrantLedger(clone), sample)
    # This successful cloned reservation is a demonstrated qualification gap.
    for p in (path, clone):
        with sqlite3.connect(p) as connection:
            assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (1,)
    assert external_trust_readout()["global_ledger_single_use"] == "BLOCKED"


def test_disposable_process_crash_rolls_back_uncommitted_transaction(sample, tmp_path):
    import subprocess
    import sys

    path = tmp_path / "crash.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    code = """
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO grant_spent VALUES ('TEST','TEST','TEST','TEST','TEST','TEST','TEST')")
os._exit(23)
"""
    result = subprocess.run([sys.executable, "-c", code, str(path)], timeout=15)
    assert result.returncode == 23
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)
    reserve(ledger, sample)


def test_source_scope_tampering_denied_even_with_new_local_hash(sample, tmp_path):
    import hashlib
    import json

    from adapters.mineflayer.self_world_stage_w_archive import canonical
    from test_self_world_stage_w_gate import _consume

    changed = json.loads(json.dumps(sample["archive"]))
    changed["native"]["source_scope"] = "unapproved_source"
    raw = canonical(changed)
    path = tmp_path / "unapproved.json"
    path.write_bytes(raw)
    ledger = StageWPersistentGrantLedger.provision_new(tmp_path / "scope.sqlite3")
    with pytest.raises(StageWGateRejected):
        _consume(sample, ledger, archive_path=path, archive_sha=hashlib.sha256(raw).hexdigest())


def test_duplicate_signed_grant_cannot_reserve_twice(sample, tmp_path):
    from test_self_world_stage_w_gate import _consume

    ledger = StageWPersistentGrantLedger.provision_new(tmp_path / "double.sqlite3")
    first = _consume(sample, ledger)
    assert not first.external_issuer_identity_qualified
    assert not first.real_s10_commit_permitted
    with pytest.raises(StageWGateRejected):
        _consume(sample, StageWPersistentGrantLedger(tmp_path / "double.sqlite3"))


def test_unsigned_handoff_cannot_invent_custody_or_capture_time(monkeypatch, tmp_path):
    import json

    from adapters.mineflayer.self_world_stage_w4_preflight import prepare_unsigned_custody_handoff
    from test_self_world_stage_w3_capture import _fixture_lines, _launch

    _launch(monkeypatch, tmp_path, _fixture_lines())
    handoff = prepare_unsigned_custody_handoff(tmp_path, received_at_utc="2026-10-19T00:00:00Z")
    assert handoff["frame_count"] == 3
    assert handoff["signature"] is None and handoff["archivist_public_key_pin"] is None
    assert handoff["capture_start_utc"] is None and handoff["capture_end_utc"] is None
    assert not handoff["independent_custody_qualified"] and not handoff["s10_permission"]
    assert json.dumps(handoff)
    with pytest.raises(W4PreworldBlocked):
        prepare_unsigned_custody_handoff(tmp_path, received_at_utc="2026-10-19T00:00:00")


def test_disposable_in_place_rollback_demonstrates_monotonic_authority_gap(sample, tmp_path):
    path = tmp_path / "rollback-copy.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    pristine = tmp_path / "pristine-copy.sqlite3"
    shutil.copy2(path, pristine)
    reserve(ledger, sample)
    # Explicitly isolated TEST storage: no actual grant/evidence is restored.
    shutil.copyfile(pristine, path)
    reserve(ledger, sample)
    assert external_trust_readout()["global_ledger_single_use"] == "BLOCKED"


def _w4_wire_probe(*, orientation=True):
    from test_mineflayer_process_session import observation_line

    payload = json.loads(observation_line())
    payload["kind"] = "probe"
    payload["request_id"] = "w4-preregistered-probe-01"
    if orientation:
        payload["snapshot"]["native_orientation"] = {
            "source": "mineflayer_bot_entity",
            "yaw_rad": math.pi / 2,
            "pitch_rad": 0.25,
        }
    return payload


def test_native_orientation_requires_exact_source_same_sample():
    payload = _w4_wire_probe()
    reading = parse_mineflayer_line(json.dumps(payload))
    sample = require_native_nh1_orientation(
        reading, expected_session="session-1",
        expected_request_id="w4-preregistered-probe-01", before_seq=2,
    )
    assert sample.observation is reading
    from dataclasses import asdict

    assert asdict(reading.snapshot)["native_orientation"]["yaw_rad"] == math.pi / 2
    assert sample.source_reference == "session-1:1"
    assert sample.yaw_rad == math.pi / 2
    plan = plan_native_nh1_placement(
        reading, expected_session="session-1",
        expected_request_id="w4-preregistered-probe-01", before_seq=2, slot=1,
    )
    assert plan.spawn.x == pytest.approx(-1)
    assert plan.spawn.z == pytest.approx(2)
    assert plan.horizontal_distance_m == 2
    assert plan.source_orientation_qualified
    assert plan.source_probe_request_id == "w4-preregistered-probe-01"
    assert plan.source_reference == "session-1:1"
    assert not plan.physical_run_permitted


@pytest.mark.parametrize("attack", (
    "missing", "foreign_session", "foreign_probe", "replay", "event",
    "missing_expected_id", "missing_expected_session", "absent_seq_bound",
))
def test_native_orientation_source_binding_rejects(attack):
    payload = _w4_wire_probe(orientation=attack != "missing")
    if attack == "event":
        payload["kind"] = "entities"
        del payload["request_id"]
    reading = parse_mineflayer_line(json.dumps(payload))
    kwargs = dict(expected_session="session-1",
                  expected_request_id="w4-preregistered-probe-01", before_seq=2)
    if attack == "foreign_session":
        kwargs["expected_session"] = "session-other"
    elif attack == "foreign_probe":
        kwargs["expected_request_id"] = "w4-other"
    elif attack == "replay":
        kwargs["before_seq"] = 1
    elif attack == "missing_expected_id":
        kwargs["expected_request_id"] = None
    elif attack == "missing_expected_session":
        kwargs["expected_session"] = None
    elif attack == "absent_seq_bound":
        kwargs["before_seq"] = None
    with pytest.raises(W4PreworldBlocked):
        require_native_nh1_orientation(reading, **kwargs)


@pytest.mark.parametrize("attack", (
    "nan", "inf", "pitch", "bool", "wrong_source", "null", "extra",
))
def test_raw_native_orientation_field_rejected(attack):
    payload = _w4_wire_probe()
    o = payload["snapshot"]["native_orientation"]
    if attack == "nan":
        o["yaw_rad"] = math.nan
    elif attack == "inf":
        o["yaw_rad"] = math.inf
    elif attack == "pitch":
        o["pitch_rad"] = math.pi
    elif attack == "bool":
        o["yaw_rad"] = True
    elif attack == "wrong_source":
        o["source"] = "operator-inferred-yaw"
    elif attack == "null":
        payload["snapshot"]["native_orientation"] = None
    else:
        o["grant"] = True
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps(payload))


def test_legacy_wire_has_no_orientation_and_is_not_w4_eligible():
    payload = _w4_wire_probe(orientation=False)
    reading = parse_mineflayer_line(json.dumps(payload))
    from dataclasses import asdict

    assert not hasattr(reading.snapshot, "native_orientation")
    assert "native_orientation" not in asdict(reading.snapshot)
    with pytest.raises(W4PreworldBlocked):
        plan_native_nh1_placement(
            reading, expected_session="session-1",
            expected_request_id="w4-preregistered-probe-01", before_seq=2, slot=1,
        )


def test_node_launch_flag_is_child_scoped_and_defaults_off(monkeypatch, tmp_path):
    import asyncio

    from adapters.mineflayer.process_session import MineflayerProcessSession
    from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
    from test_mineflayer_process_session import FakeProcess, started_line

    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// test fixture", encoding="utf-8")
    captured = []

    async def fake_launch(*_args, **kwargs):
        captured.append(kwargs)
        return FakeProcess([started_line()])

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_launch)
    # Inherited opt-in MUST be removed from default S49/R/V launch.
    monkeypatch.setenv("RELAYSELF_W4_NH1_ORIENTATION_V0", "1")

    async def exercise():
        await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(version="1.21.8"), bridge_path=bridge,
        )
        await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(version="1.21.8"), bridge_path=bridge,
            w4_native_orientation_dev=True,
        )

    asyncio.run(exercise())
    assert "RELAYSELF_W4_NH1_ORIENTATION_V0" not in captured[0]["env"]
    assert captured[1]["env"]["RELAYSELF_W4_NH1_ORIENTATION_V0"] == "1"


def test_node_orientation_opt_in_rejects_wrong_version_before_spawn(tmp_path):
    import asyncio

    from adapters.mineflayer.process_session import (
        MineflayerProcessSession,
        MineflayerProcessStartError,
    )
    from adapters.mineflayer.python_protocol import MineflayerLaunchConfig

    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// test fixture", encoding="utf-8")
    with pytest.raises(MineflayerProcessStartError, match="pinned Minecraft"):
        asyncio.run(MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            w4_native_orientation_dev=True,
        ))


def test_native_orientation_caller_cursor_rejects_stale_and_duplicate():
    reading = parse_mineflayer_line(json.dumps(_w4_wire_probe()))
    kwargs = dict(expected_session=reading.session_id, expected_request_id=reading.request_id,
                  before_seq=10)
    for cursor in ({'minimum_seq': 2}, {'seen_source_refs': frozenset({'session-1:1'})}):
        with pytest.raises(W4PreworldBlocked):
            require_native_nh1_orientation(reading, **kwargs, **cursor)


def _oriented_closed():
    from dataclasses import fields

    from adapters.mineflayer.python_protocol import (
        MineflayerNativeOrientation,
        MineflayerOrientedSnapshot,
        MineflayerSnapshot,
    )

    w = sf._synthetic_targeted_witness(0, .2)  # S16 executes but Stage S stays HOLD.
    def orient(o, yaw):
        return replace(o, snapshot=MineflayerOrientedSnapshot(
            **{f.name: getattr(o.snapshot, f.name) for f in fields(MineflayerSnapshot)},
            native_orientation=MineflayerNativeOrientation('mineflayer_bot_entity', yaw, .2),
        ))
    w = replace(w, original_probe=replace(orient(w.original_probe, -math.pi/2), seq=2))
    world = w.consequence
    shift = 3
    world = replace(world,
        before_observation=replace(orient(world.before_observation, -.4),
                                   seq=world.before_observation.seq+shift),
        after_observation=replace(orient(world.after_observation, .9),
                                  seq=world.after_observation.seq+shift),
        dispatch_receipt=replace(world.dispatch_receipt, seq=world.dispatch_receipt.seq+shift),
        cleanup_receipt=replace(world.cleanup_receipt, seq=world.cleanup_receipt.seq+shift))
    w = replace(w, consequence=world)
    staging = replace(w.original_probe, seq=1, request_id='nh1-staging-1')
    return staging, w


def test_oriented_s16_roundtrip_and_nh1_readonly_receipt():
    from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
    from adapters.mineflayer.self_world_stage_w4_preflight import (
        capture_w4_oriented_evidence,
        readback_nh1_slot,
        verify_w4_oriented_evidence,
    )

    staging, w = _oriented_closed()
    evidence = capture_w4_oriented_evidence(w.consequence)
    reread = json.loads(json.dumps(evidence))
    verify_w4_oriented_evidence(reread, consequence=w.consequence)
    assert reread['decoded_action'] == capture_native_action_evidence(w.consequence)
    assert reread['decoded_action']['before_observation']['snapshot']['native_orientation'][
        'yaw_rad'] == -.4
    assert reread['decoded_action']['after_observation']['snapshot']['native_orientation'][
        'yaw_rad'] == .9
    receipt = readback_nh1_slot(staging, w, slot=1, expected_session=staging.session_id,
                                expected_request_id=staging.request_id, minimum_seq=1)
    assert receipt['stage_s_direction'] == 'hold'
    assert receipt['observed_zombie_id'] == w.original_probe.snapshot.nearby_entities[0].entity_id
    assert receipt['physical_run_permitted'] is False
    assert receipt['source_pair_trace']['probe_seq'] == w.original_probe.seq
    assert receipt['source_pair_trace']['orientation_seq'] == staging.seq
    assert not receipt['signed_evidence']


@pytest.mark.parametrize('attack', ('post_attached', 'before_after_swap', 'foreign', 'legacy',
                                   'probe_swap', 'bad_angle', 'extra_trust'))
def test_oriented_evidence_extension_denies_tampering(attack):
    import copy

    from adapters.mineflayer.self_world_stage_w4_preflight import (
        capture_w4_oriented_evidence,
        verify_w4_oriented_evidence,
    )

    _, w = _oriented_closed()
    e = copy.deepcopy(capture_w4_oriented_evidence(w.consequence))
    before = e['decoded_action']['before_observation']
    if attack == 'post_attached':
        before['snapshot']['native_orientation'] = e['decoded_action'][
            'after_observation']['snapshot']['native_orientation']
    elif attack == 'before_after_swap':
        before['seq'] = e['decoded_action']['after_observation']['seq']
    elif attack == 'foreign':
        before['session_id'] = 'foreign'
    elif attack == 'legacy':
        del before['snapshot']['native_orientation']
    elif attack == 'probe_swap':
        before['request_id'] = 'foreign-probe'
    elif attack == 'bad_angle':
        before['snapshot']['native_orientation']['pitch_rad'] = math.inf
    else:
        e['signed_evidence'] = True
    with pytest.raises(W4PreworldBlocked):
        verify_w4_oriented_evidence(e, consequence=w.consequence)


@pytest.mark.parametrize('attack', ('after_orientation', 'foreign', 'wrong_probe',
                                   'wrong_target_position', 'duplicate', 'near_wait'))
def test_nh1_staging_source_or_near_wait_denied(attack):
    from adapters.mineflayer.self_world_stage_w4_preflight import readback_nh1_slot

    staging, w = _oriented_closed()
    kwargs = dict(slot=1, expected_session=staging.session_id,
                  expected_request_id=staging.request_id, minimum_seq=1)
    if attack == 'after_orientation':
        staging = replace(staging, seq=w.consequence.after_observation.seq)
    elif attack == 'foreign':
        staging = replace(staging, session_id='foreign')
    elif attack == 'wrong_probe':
        kwargs['expected_request_id'] = 'wrong'
    elif attack == 'wrong_target_position':
        staging = replace(staging, snapshot=replace(staging.snapshot,
                          position=MineflayerPosition(99, 64, 99)))
    elif attack == 'duplicate':
        kwargs['seen_source_refs'] = frozenset({staging.provenance.reference})
    else:
        w = None
    with pytest.raises(W4PreworldBlocked):
        readback_nh1_slot(staging, w, **kwargs)


def test_all_two_slots_retained_and_no_physical_entry():
    from adapters.mineflayer.self_world_stage_w4_preflight import nh1_preflight_inventory

    report = nh1_preflight_inventory(dev_opt_in=True)
    assert [row['slot'] for row in report['near_slots']] == [1, 2]
    assert all(row['status'] == 'PREWORLD_BLOCKED' for row in report['near_slots'])
    assert not report['physical_run_permitted']
    for kwargs in ({}, {'dev_opt_in': True, 'run_physical': True}):
        with pytest.raises(W4PreworldBlocked):
            nh1_preflight_inventory(**kwargs)


@pytest.mark.parametrize('oriented', (False, True))
def test_original_executor_s16_preserves_schema_selected_before_action(monkeypatch, oriented):
    from dataclasses import fields

    import test_action_feedback_qualification as s17
    from adapters.mineflayer.python_protocol import (
        MineflayerNativeOrientation,
        MineflayerOrientedSnapshot,
        MineflayerSnapshot,
    )
    from adapters.mineflayer.self_action_evidence import (
        capture_native_action_evidence,
        verify_native_action_evidence,
    )
    from adapters.mineflayer.self_world_stage_w4_preflight import capture_w4_oriented_evidence

    original_observation = s17.observation
    def observe(seq, x, z):
        o = original_observation(seq, x, z)
        if not oriented:
            return o
        return replace(o, snapshot=MineflayerOrientedSnapshot(
            **{f.name: getattr(o.snapshot, f.name) for f in fields(MineflayerSnapshot)},
            native_orientation=MineflayerNativeOrientation('mineflayer_bot_entity', seq/10, .1)))
    monkeypatch.setattr(s17, 'observation', observe)
    *_, world, interpretation, terminal = s17.executed_closed_chain()
    assert terminal.state.value == 'outcome'
    assert interpretation.reason_code == 'observed_execution'
    e = json.loads(json.dumps(capture_native_action_evidence(world)))
    verify_native_action_evidence(e, action_id=world.action_id, session_id=world.session_id,
                                  movement_m=world.movement_distance)
    for key in ('before_observation', 'after_observation'):
        assert ('native_orientation' in e[key]['snapshot']) is oriented
    if oriented:
        assert capture_w4_oriented_evidence(world)['decoded_action'] == e
    else:
        with pytest.raises(W4PreworldBlocked):
            capture_w4_oriented_evidence(world)


@pytest.mark.parametrize('attack', ('duplicate', 'session', 'missing'))
def test_oriented_stream_decoder_denies_duplicate_foreign_and_gap(attack):
    from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
    from test_mineflayer_process_session import started_line

    decoder = MineflayerStreamDecoder()
    decoder.decode(started_line().decode())
    payload = _w4_wire_probe()
    decoder.decode(json.dumps(payload))
    if attack == 'session':
        payload.update(session_id='other', seq=2)
    elif attack == 'missing':
        payload['seq'] = 3
    with pytest.raises(MineflayerAdapterProtocolError):
        decoder.decode(json.dumps(payload))


@pytest.mark.parametrize('yaw', (0, math.pi, -math.pi, 2*math.pi, -2*math.pi, 1e10))
@pytest.mark.parametrize('pitch', (-math.pi/2, math.pi/2))
def test_horizontal_geometry_at_pitch_and_yaw_boundaries(yaw, pitch):
    payload = _w4_wire_probe()
    payload['snapshot']['native_orientation'].update(yaw_rad=yaw, pitch_rad=pitch)
    reading = parse_mineflayer_line(json.dumps(payload))
    plan = plan_native_nh1_placement(reading, expected_session=reading.session_id,
                                   expected_request_id=reading.request_id, before_seq=2, slot=2)
    p = reading.snapshot.position
    assert math.hypot(plan.spawn.x-p.x, plan.spawn.z-p.z) == pytest.approx(2)
    assert plan.spawn.y == p.y


def test_w4_oriented_probe_survives_original_w3_byte_capture(monkeypatch, tmp_path):
    from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout
    from test_mineflayer_process_session import started_line
    from test_self_world_stage_w3_capture import _ack, _launch

    payload = _w4_wire_probe()
    lines = [started_line(), (json.dumps(payload)+'\n').encode(), _ack()]
    session, _ = _launch(monkeypatch, tmp_path, lines)
    raw = (tmp_path / 'w3-node-stdout.raw.jsonl').read_bytes()
    assert raw == b''.join(lines)
    assert audit_w3_sealed_stdout(tmp_path) == session.raw_capture_receipt
    reading = parse_mineflayer_line(raw.splitlines()[1].decode())
    assert require_native_nh1_orientation(
        reading, expected_session='session-1', expected_request_id=payload['request_id'],
        before_seq=2).yaw_rad == math.pi/2
    assert session.raw_capture_receipt['external_source_independence_attested'] is False
