"""I2g CPU-only end-to-end source/seal/fork/first I2f preflight fixture.

All Paper and Native bytes are deliberately SYNTHESIZED IN THIS TEST.
The positive outcome only validates audit contracts, never real World.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import parse_mineflayer_line
from experiments.i_lane_i2g_independent_origin_audit_dev import (
    I2gIndependentOriginHold,
    independently_read_i2g_original,
    prepare_i2g_inert_fork_and_pins_once,
    seal_i2g_original_manifest_once,
)
from relay_self.coordinated_autosave_runtime_dev import StoppedWorldReceipt
from relay_self.i_lane_i2f_future_source_pins_dev import (
    inspect_i2f_future_original_sources,
)
from relay_self.innate_schema import SchemaSnapshot
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from relay_self.world_resident_lifecycle_dev import WorldLifetime
from test_mineflayer_process_session import observation_line
from test_stage28b_retired_typed_cut_dev import _setup


def _bytes(value: dict) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode()


def _frozen_native(req: str, native: str, seq: int):
    item = json.loads(observation_line())
    item.update(type="observation", kind="probe", seq=seq,
                request_id=req, session_id=native)
    parsed = parse_mineflayer_line(_bytes(item).decode())
    tick = (parsed.snapshot.time.day * 24000
            + parsed.snapshot.time.time_of_day)
    return _bytes(item), tick


def _fake_original(tmp_path, monkeypatch):
    # Re-capture a complete ORIGINAL typed generation at the NEW I2g branch.
    # Never rewrite a committed generation's branch or relax the auditor.
    bridge, paper, store, staging = _setup(tmp_path, monkeypatch)
    for dim in ("world_nether", "world_the_end"):
        folder = tmp_path / dim / "region"
        folder.mkdir(parents=True)
        (folder / "r.0.0.mca").write_bytes(b"test-only-dimension")
    synthetic_world_uuid = "11111111-2222-4333-8444-555555555555"
    paper.world_id = synthetic_world_uuid
    paper.branch_id = "p0d-real-resident-presence"
    bridge.lifecycle.world = WorldLifetime(
        synthetic_world_uuid, "p0d-real-resident-presence",
        "paper-owned-original", 0, 100,
    )
    def stop_paper():
        paper.stop_count += 1
        paper.owned_session_id = None
        return StoppedWorldReceipt(
            synthetic_world_uuid, "p0d-real-resident-presence",
            "paper-owned-original", 110,
            "paper:main-thread-tick:110",
            "paper:owned-process-exit:0", 0, True,
        )
    paper.stop_and_save = stop_paper
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        owner.retained = replace(
            owner.retained, pattern_registry=owner.pattern_registry,
        )
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    for sid in ("A", "B"):
        resident.register_present_schema(sid, SchemaSnapshot(sid, 0, ()))
        resident.bind_login(
            self_id=sid, native_session_id=bridge.owners[sid].native_session_id,
            world_epoch=0, world_tick=105,
        )
    for sid in ("A", "B"):
        resident.fence_self(sid)
        finished = asyncio.run(resident.retire_self(sid))
        resident.mark_offline(finished)
    prepared = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=staging,
    )
    evidence = tmp_path / "i2g-original-source-fixture"
    evidence.mkdir()
    generation = evidence / "typed-world-self-generations" / prepared.generation.name
    generation.parent.mkdir()
    shutil.copytree(prepared.generation, generation)
    world_id = synthetic_world_uuid
    paper_session = "paper-owned-i2g-fixture"
    boot = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
    actors = {
        "A": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
        "B": "cccccccc-cccc-4ccc-cccc-cccccccccccc",
    }
    paper = [
        f"P0D_RESIDENT_READY boot={boot} source=PAPER_MAIN_THREAD version=1\n",
    ]
    seq = [
        ("A", "JOIN"), ("B", "JOIN"),
        ("A", "PRESENT"), ("B", "PRESENT"),
        ("A", "QUIT"), ("B", "PRESENT"),
        ("A", "JOIN"), ("A", "PRESENT"),
        ("A", "QUIT"), ("B", "QUIT"),
    ]
    for tick, (sid, event) in enumerate(seq, 5):
        paper.append(
            f"P0D_RESIDENT event={event} boot={boot} tick={tick} "
            f"world={world_id} actor={actors[sid]} name=Relay{sid} "
            "x=0 y=64 z=0 source=PAPER_MAIN_THREAD\n"
        )
    paper.extend(["Saved the game\n", "Stopping server\n"])
    (evidence / (paper_session + ".log")).write_bytes("".join(paper).encode())
    (evidence / (paper_session + ".pid")).write_text("130\n")
    # Final IDs MUST equal the original committed A/B Owner cuts.
    # A's first Native belongs to an older, now retired session.
    original_ids = {
        "A0": "native-born-A-first",
        "B0": "native-retired-B",
        "A1": "native-retired-A",
    }
    originals = {}
    raw_native = []
    for key, native in original_ids.items():
        sid = key[0]
        login_req = "original-probe-" + key
        login, tick = _frozen_native(login_req, native, 1)
        commands = [_bytes({"type": "observe", "request_id": login_req})]
        stdout = [login]
        if key == "B0":
            manual_req = "original-b-continuing-probe"
            reply, _ = _frozen_native(manual_req, native, 2)
            stdout.append(reply)
            commands.append(_bytes({
                "type": "observe", "request_id": manual_req,
            }))
        login_ref = {
            "self_id": sid,
            "login_seq": 2 if key == "A1" else 1,
            "world_id": world_id,
            "branch_id": "p0d-real-resident-presence",
            "paper_session_id": paper_session,
            "world_epoch": 0,
            "native_session_id": native,
            "observation_ref": login_req,
            "observed_world_tick": tick,
            "old_native_invalidated": True,
            "physical_wal_clear": True,
            "stale_gpu_fenced": True,
            "stale_transport_fenced": True,
            "new_native_source_verified": True,
            "action_issue_authorized": False,
        }
        originals[key] = login_ref
        name = "Relay" + sid
        out = evidence / f"i2g-native-{name}-{native}.jsonl"
        command = evidence / f"i2g-commands-{name}-{native}.jsonl"
        out.write_bytes(b"".join(stdout))
        command.write_bytes(b"".join(commands))
        raw_native.append({
            "username": name, "native_session_id": native,
            "pid": 110 if key == "A0" else 111 if key == "B0" else 112,
            "raw_stdout_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "raw_stdin_sha256": hashlib.sha256(command.read_bytes()).hexdigest(),
            "raw_stdout_bytes": out.stat().st_size,
            "raw_stdin_bytes": command.stat().st_size,
        })
    initials = [
        [sid, hashlib.sha256(
            (generation / "selves" / sid / "cognition.json").read_bytes()
        ).hexdigest()] for sid in ("A", "B")
    ]
    trial = {
        "world_uuid": world_id,
        "paper_session_id": paper_session,
        "typed_world_self_generation": str(generation),
        "b_actual_physical_action": False,
        "b_move_action_causality": False,
        "real_l1_l2_gpu_executed": False,
        "i2g_initial_exploration_pattern_learned": False,
        "i2g_initial_physical_action_issued": False,
        "i2g_original_issuer_observation_only": True,
        "a_actor_uuid": actors["A"],
        "b_actor_uuid": actors["B"],
        "a_paper_quit_tick": 9,
        "b_paper_continuation_tick": 10,
        "a_paper_rejoin_tick": 11,
        "a_original_native_session": original_ids["A0"],
        "b_original_native_session": original_ids["B0"],
        "i2g_original_first_login_evidence": {
            "A": originals["A0"], "B": originals["B0"],
        },
        "a_relogin_evidence": originals["A1"],
        "b_probe": {
            "session": original_ids["B0"],
            "request_id": "original-b-continuing-probe",
        },
    }
    report = {
        "classification": (
            "I2G_REAL_ORIGINAL_V3_TYPED_A_B_CAPTURED_AUDIT_PENDING"
        ),
        "i2g_original_v3_source": True,
        "i2g_initial_source_verified": True,
        "i2g_source_manifest_independent_verified": False,
        "real_gpu": False,
        "real_b_physical_action": False,
        "autonomous_l1_skill_selection": False,
        "steps": [trial], "world_uuid": world_id,
        "typed_world_self_generation": str(generation),
        "i2g_original_raw_native": raw_native,
        "i2g_initial_schema_receipt": {
            "self_ids": ["A", "B"],
            "born_initial_only": True,
            "learning_claimed": False,
            "physical_action_authorized": False,
            "original_registry_revisions": [["A", 0], ["B", 0]],
            "schema_modes": [
                ["A", "NO_EXPLORATION_MODULE"],
                ["B", "NO_EXPLORATION_MODULE"],
            ],
            "initial_cognition_sha256": initials,
        },
    }
    (evidence / "resident-presence-result.json").write_bytes(_bytes(report))
    return evidence, generation, report


def test_i2g_full_raw_origin_to_sealed_manifest_to_inert_fork_CPU_only(
    tmp_path, monkeypatch,
):
    evidence, generation, report = _fake_original(tmp_path, monkeypatch)
    review = independently_read_i2g_original(
        evidence=evidence, generation=generation,
    )
    assert review.same_generation_born_v3
    assert review.real_model_post_count == 0
    assert review.original_world_actually_executed_by_auditor is False
    assert len(review.original_native_ids) == 3
    checked, manifest_sha, count = seal_i2g_original_manifest_once(
        evidence=evidence, generation=generation,
    )
    assert checked == review and count > 0
    assert hashlib.sha256(
        (evidence / "SHA256SUMS").read_bytes()
    ).hexdigest() == manifest_sha
    with pytest.raises(I2gIndependentOriginHold):
        seal_i2g_original_manifest_once(
            evidence=evidence, generation=generation,
        )
    fork = tmp_path / "new-restored-i2f"
    pins_file = tmp_path / "external-i2f-source-pins.json"
    pins = prepare_i2g_inert_fork_and_pins_once(
        evidence=evidence, generation=generation,
        sealed_manifest_sha256=manifest_sha,
        manifest_files=count, destination=fork,
        restore_id="i2g-fixture-only", pins_output=pins_file,
    )
    assert json.loads(pins_file.read_bytes())["source_world_id"] == (
        "11111111-2222-4333-8444-555555555555"
    )
    assert pins.source_committed_sha256 == review.source_committed_sha256
    assert pins.original_manifest_sha256 == manifest_sha
    assert pins.original_manifest_files == count
    history, future = inspect_i2f_future_original_sources(
        generation=generation, restored=fork,
        original_evidence=evidence, pins=pins,
    )
    assert set(history.historical_native_sessions) == set(review.original_native_ids)
    assert future.schema_recovered_a_b
    assert future.original_selves_offline
    assert future.model_post_count == 0
    assert not future.paper_started
    assert not future.physical_action_issue_authorized
    # Nothing in this test starts Minecraft, so no REAL_WORLD_PASS classification.


@pytest.mark.parametrize("fault", [
    "foreign-native", "stale-a-probe", "move-command",
    "paper-actor", "paper-present", "tampered-owner",
    "learned-pattern-claim", "corrupt-stdout",
    "paper-cross-actor", "paper-duplicate-epoch", "paper-b-quit-first",
    "paper-false-b-receipt", "paper-tampered-pid", "paper-no-save",
    "paper-native-pid-collision", "native-foreign-boot",
    "issuer-not-observation-only",
    "native-unretired-issuer", "native-extra-observe",
    "native-probe-without-stdin",
])
def test_i2g_source_seal_rejects_hostile_original_evidence_CPU_only(
    tmp_path, monkeypatch, fault,
):
    evidence, generation, report = _fake_original(tmp_path, monkeypatch)
    path = evidence / "resident-presence-result.json"
    if fault == "foreign-native":
        report["steps"][0]["a_relogin_evidence"]["native_session_id"] = (
            "native-foreign-A"
        )
    elif fault == "stale-a-probe":
        report["steps"][0]["a_relogin_evidence"]["observation_ref"] = (
            "fake-observe-id"
        )
    elif fault == "move-command":
        command = next(evidence.glob("i2g-commands-RelayA-native-retired-A.jsonl"))
        command.write_bytes(_bytes({"type": "move", "request_id": "harm"}))
        report["i2g_original_raw_native"][2]["raw_stdin_sha256"] = hashlib.sha256(
            command.read_bytes()
        ).hexdigest()
        report["i2g_original_raw_native"][2]["raw_stdin_bytes"] = command.stat().st_size
    elif fault == "paper-actor":
        paper = evidence / "paper-owned-i2g-fixture.log"
        paper.write_text(paper.read_text().replace(
            "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "foreign-actor",
        ))
    elif fault == "paper-present":
        paper = evidence / "paper-owned-i2g-fixture.log"
        paper.write_text(paper.read_text().replace("event=PRESENT", "event=ABSENT"))
    elif fault == "paper-cross-actor":
        paper = evidence / "paper-owned-i2g-fixture.log"
        paper.write_text(paper.read_text().replace(
            "actor=" + "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
            + " name=RelayA x=0 y=64 z=0 source=PAPER_MAIN_THREAD",
            "actor=" + "cccccccc-cccc-4ccc-cccc-cccccccccccc"
            + " name=RelayA x=0 y=64 z=0 source=PAPER_MAIN_THREAD",
            1,
        ))
    elif fault == "paper-duplicate-epoch":
        paper = evidence / "paper-owned-i2g-fixture.log"
        text = paper.read_text()
        paper.write_text(text.replace(
            "event=QUIT boot=", "event=JOIN boot=", 1,
        ))
    elif fault == "paper-b-quit-first":
        paper = evidence / "paper-owned-i2g-fixture.log"
        text = paper.read_text()
        paper.write_text(text.replace(
            "event=PRESENT boot=", "event=QUIT boot=", 1,
        ))
    elif fault == "paper-false-b-receipt":
        report["steps"][0]["b_paper_continuation_tick"] = 8888
    elif fault == "paper-tampered-pid":
        (evidence / "paper-owned-i2g-fixture.pid").write_text("not-pid\n")
    elif fault == "paper-no-save":
        paper = evidence / "paper-owned-i2g-fixture.log"
        paper.write_text(paper.read_text().replace("Saved the game", "NO SAVE"))
    elif fault == "paper-native-pid-collision":
        report["i2g_original_raw_native"][0]["pid"] = 130
    elif fault == "issuer-not-observation-only":
        report["steps"][0]["i2g_original_issuer_observation_only"] = False
    elif fault == "native-foreign-boot":
        report["steps"][0]["i2g_original_first_login_evidence"]["A"][
            "paper_session_id"
        ] = "paper-owned-foreign"
    elif fault == "native-unretired-issuer":
        report["steps"][0]["a_relogin_evidence"]["action_issue_authorized"] = True
    elif fault == "native-extra-observe":
        commands = evidence / "i2g-commands-RelayA-native-born-A-first.jsonl"
        with commands.open("ab") as output:
            output.write(_bytes({
                "type": "observe", "request_id": "unanswered-extra-observation",
            }))
        row = report["i2g_original_raw_native"][0]
        row["raw_stdin_sha256"] = hashlib.sha256(
            commands.read_bytes()
        ).hexdigest()
        row["raw_stdin_bytes"] = commands.stat().st_size
    elif fault == "native-probe-without-stdin":
        commands = evidence / "i2g-commands-RelayA-native-born-A-first.jsonl"
        commands.write_bytes(_bytes({
            "type": "observe", "request_id": "wrong-request",
        }))
        row = report["i2g_original_raw_native"][0]
        row["raw_stdin_sha256"] = hashlib.sha256(
            commands.read_bytes()
        ).hexdigest()
        row["raw_stdin_bytes"] = commands.stat().st_size
    elif fault == "tampered-owner":
        owner = generation / "selves" / "A" / "cognition.json"
        owner.write_bytes(b"changed cognition")
    elif fault == "learned-pattern-claim":
        report["i2g_initial_schema_receipt"]["learning_claimed"] = True
    else:
        source = evidence / "i2g-native-RelayB-native-retired-B.jsonl"
        source.write_bytes(b"forged Native stdout\n")
    if fault in {
        "foreign-native", "stale-a-probe", "move-command", "learned-pattern-claim",
        "paper-false-b-receipt", "paper-native-pid-collision",
        "native-foreign-boot", "native-unretired-issuer",
        "native-extra-observe", "native-probe-without-stdin",
        "issuer-not-observation-only",
    }:
        path.write_bytes(_bytes(report))
    with pytest.raises(I2gIndependentOriginHold):
        seal_i2g_original_manifest_once(
            evidence=evidence, generation=generation,
        )
    assert not (evidence / "SHA256SUMS").exists()
