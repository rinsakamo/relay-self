"""Stage W1: pinned offline archive + separate signer + restart-safe ledger.

Everything uses SYNTHETIC S49 fixtures and ephemeral test signer keys.
No genuine physical World, external issuer trust, or S10 update.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest

import test_self_world_stage_s_feedback as sf
from adapters.mineflayer.self_world_stage_v_attestation import (
    fingerprint_for_public_pem,
    request_from_existing_world,
)
from adapters.mineflayer.self_world_stage_w_archive import (
    audit_independent_source_extract,
    canonical,
)
from adapters.mineflayer.self_world_stage_w_gate import (
    StageWGateRejected,
    StageWOfflineConsumer,
    StageWPersistentGrantLedger,
)


def _vec(p):
    return [p.x, p.y, p.z]


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage-w1-disposable-source")
    witness = sf._synthetic_targeted_witness(0.5, 0.0)
    world = witness.consequence
    original, before, after = (
        witness.original_probe, world.before_observation, world.after_observation,
    )
    assert before is not None and after is not None
    next_probe = replace(
        original, seq=after.seq + 3,
        request_id=f"s49-actual:{original.session_id}:event-{after.seq + 2}",
    )
    expected = request_from_existing_world(
        run_id="stage-w1-disposable-001",
        closed=witness, following_probe=next_probe,
    )
    outcome = sf.assess_stage_s_original_separation(
        witness, sf.StageSPredeclaredSeparationRule(),
    )
    typed = outcome.typed_s17
    assert typed is not None and typed.feedback is not None
    target_id = outcome.entity_id
    assert target_id is not None

    def entity(frame):
        return next(e for e in frame.snapshot.nearby_entities
                    if e.entity_id == target_id)

    source = {
        "session_id": original.session_id,
        "original_seq": original.seq,
        "original_request_id": original.request_id,
        "action_id": witness.terminal.action_id,
        "binding_id": world.binding_id,
        "before_seq": before.seq,
        "after_seq": after.seq,
        "before_health": before.snapshot.health,
        "after_health": after.snapshot.health,
        "before_target_m": outcome.distance_before_m,
        "after_target_m": outcome.distance_after_m,
        "target_id": target_id,
        "world_provenance": asdict(world.provenance),
        "outcome_ref": typed.outcome_ref,
        "feedback_id": typed.feedback.feedback_id,
        "next_probe_seq": next_probe.seq,
        "next_probe_request_id": next_probe.request_id,
    }
    b, a = before.snapshot.position, after.snapshot.position
    native = {
        "source_scope": "mineflayer_entity_registry",
        "complete_registry": True,
        "original_bot_xyz": _vec(original.snapshot.position),
        "original_target_xyz": _vec(entity(original).position),
        "before_bot_xyz": _vec(b),
        "before_target_xyz": _vec(entity(before).position),
        "after_bot_xyz": _vec(a),
        "after_target_xyz": _vec(entity(after).position),
        "horizontal_movement_m": math.hypot(a.x-b.x, a.z-b.z),
    }
    archive = {
        "schema": "stage-w1-source-extract-v0",
        "run_id": expected.run_id,
        "source": source,
        "native": native,
        "terminal": {
            "action_state": witness.terminal.state.value,
            "disposition": witness.interpretation.disposition.value,
            "outcome_reason": witness.interpretation.reason_code,
            "action_ref": witness.interpretation.action_ref,
            "world_status": world.status.value,
            "intent_id": witness.terminal.intent_id,
        },
    }
    archive_path = root / "independent-original-source.json"
    archive_path.write_bytes(canonical(archive))
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    # The independent consumer's archive pin is passed separately, never
    # read from the request, and this fixture openly self-mints that pin.
    assert audit_independent_source_extract(
        archive_path=archive_path,
        expected_archive_sha256=archive_hash,
        expected=expected,
    ).source_sha256 == expected.evidence_sha256

    private = root / "issuer-private.pem"
    public = root / "issuer-public.pem"
    assert shutil.which("openssl"), "OpenSSL needed for real subprocess signing"
    gen = subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA",
         "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)],
        capture_output=True, check=False, timeout=30,
    )
    assert gen.returncode == 0, gen.stderr.decode()
    export = subprocess.run(
        ["openssl", "pkey", "-in", str(private),
         "-pubout", "-out", str(public)],
        capture_output=True, check=False, timeout=15,
    )
    assert export.returncode == 0, export.stderr.decode()
    req_path, signed_path = root/"request.json", root/"signed-envelope.json"
    req_path.write_bytes(canonical(asdict(expected)))
    issued = subprocess.run(
        [sys.executable, "-m",
         "adapters.mineflayer.self_world_stage_v_attestation",
         "--request", str(req_path),
         "--private-key", str(private),
         "--public-key", str(public),
         "--output", str(signed_path)],
        capture_output=True, check=False, timeout=30,
    )
    assert issued.returncode == 0, issued.stderr.decode()
    return {
        "request": expected, "envelope": json.loads(signed_path.read_text()),
        "archive": archive, "archive_path": archive_path,
        "archive_sha": archive_hash, "public": public.read_bytes(),
    }


def _new_ledger(tmp_path):
    return StageWPersistentGrantLedger.provision_new(
        (tmp_path/"spent.sqlite3").resolve(),
    )


def _consumer(sample, ledger):
    return StageWOfflineConsumer(
        pinned_public_pem=sample["public"],
        pinned_public_fingerprint=fingerprint_for_public_pem(sample["public"]),
        expected_run_id=sample["request"].run_id,
        ledger=ledger,
    )


def _consume(sample, ledger, **kwargs):
    return _consumer(sample, ledger).verify_and_reserve_once(
        envelope=kwargs.get("envelope", sample["envelope"]),
        expected=kwargs.get("request", sample["request"]),
        independent_archive_path=kwargs.get(
            "archive_path", sample["archive_path"],
        ),
        independently_pinned_archive_sha256=kwargs.get(
            "archive_sha", sample["archive_sha"],
        ),
    )


def test_w1_actual_signed_process_source_audit_durable_consumption_and_restart(
    sample, tmp_path,
):
    ledger = _new_ledger(tmp_path)
    receipt = _consume(sample, ledger)
    assert receipt.persistent_grant_reserved
    assert receipt.independent_source_recomputed
    assert receipt.signed_evidence_sha256 == sample["request"].evidence_sha256
    assert receipt.pinned_source_sha256 == sample["archive_sha"]
    assert not receipt.external_issuer_identity_qualified
    assert not receipt.raw_world_stream_qualified
    assert not receipt.real_s10_commit_permitted
    assert not receipt.physical_wait_permitted
    assert not receipt.science_qualified

    # Object recreation simulates process restart: sqlite3 durable UNIQUE
    # survives loss of the in-memory Stage V used-key set.
    restarted = StageWPersistentGrantLedger((tmp_path/"spent.sqlite3").resolve())
    with pytest.raises(StageWGateRejected, match="spent"):
        _consume(sample, restarted)
    with sqlite3.connect(tmp_path/"spent.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (1,)


def test_w1_concurrent_consumers_only_one_wins(sample, tmp_path):
    ledger = _new_ledger(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(pool.map(
            lambda _: _attempt(sample, ledger), range(2),
        ))
    assert sorted(attempts) == ["accepted", "rejected"]
    with sqlite3.connect(tmp_path/"spent.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (1,)


def _attempt(sample, ledger):
    try:
        _consume(sample, ledger)
        return "accepted"
    except StageWGateRejected:
        return "rejected"


@pytest.mark.parametrize("bad", (
    "missing_ledger", "missing_table", "wrong_key_pin",
    "wrong_run", "alter_signed", "mismatch_archive_pin",
    "wrong_archive_path", "symlink_archive",
))
def test_w1_missing_trust_anchor_or_bad_ledger_fail_closed(sample, tmp_path, bad):
    ledger = _new_ledger(tmp_path)
    if bad == "missing_ledger":
        with pytest.raises(StageWGateRejected):
            StageWPersistentGrantLedger((tmp_path/"absent.sqlite3").resolve())
        return
    if bad == "missing_table":
        with sqlite3.connect(tmp_path/"spent.sqlite3") as db:
            db.execute("DROP TABLE grant_spent")
        with pytest.raises(StageWGateRejected):
            _consume(sample, ledger)
        return
    if bad == "wrong_key_pin":
        with pytest.raises(StageWGateRejected):
            StageWOfflineConsumer(
                pinned_public_pem=sample["public"],
                pinned_public_fingerprint="0"*64,
                expected_run_id=sample["request"].run_id,
                ledger=ledger,
            )
        return
    if bad == "wrong_run":
        consumer = StageWOfflineConsumer(
            pinned_public_pem=sample["public"],
            pinned_public_fingerprint=fingerprint_for_public_pem(sample["public"]),
            expected_run_id="stage-w1-foreign-run-002",
            ledger=ledger,
        )
        with pytest.raises(StageWGateRejected):
            consumer.verify_and_reserve_once(
                envelope=sample["envelope"],
                expected=sample["request"],
                independent_archive_path=sample["archive_path"],
                independently_pinned_archive_sha256=sample["archive_sha"],
            )
        return
    options = {}
    if bad == "alter_signed":
        changed = json.loads(json.dumps(sample["envelope"]))
        changed["request"]["direction"] = "increase"
        changed["request"]["proposed_value"] = 5
        options["envelope"] = changed
    elif bad == "mismatch_archive_pin":
        options["archive_sha"] = "0"*64
    elif bad == "wrong_archive_path":
        options["archive_path"] = tmp_path/"missing-source.json"
    else:
        link = tmp_path/"linked-source.json"
        link.symlink_to(sample["archive_path"])
        options["archive_path"] = link
    with pytest.raises(StageWGateRejected):
        _consume(sample, ledger, **options)
    with sqlite3.connect(tmp_path/"spent.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)


@pytest.mark.parametrize("bad", (
    "source_distance", "source_feedback", "source_outcome",
    "native_bot", "native_target", "movement", "native_truncated",
    "terminal_unknown", "wrong_action_ref", "swapped_run",
    "next_event", "unqualified_hold", "post_seq_replay",
    "source_sha_under_signed", "extra_archive_key", "noncanonical_bytes",
))
def test_w1_offline_archive_raw_and_geometry_negative_controls(
    sample, tmp_path, bad,
):
    src = json.loads(json.dumps(sample["archive"]))
    if bad == "source_distance":
        src["source"]["after_target_m"] += 0.1
    elif bad == "source_feedback":
        src["source"]["feedback_id"] = "fake-feedback"
    elif bad == "source_outcome":
        src["source"]["outcome_ref"] = "forged"
    elif bad == "native_bot":
        src["native"]["after_bot_xyz"][0] += 1
    elif bad == "native_target":
        src["native"]["before_target_xyz"][0] += 3
    elif bad == "movement":
        src["native"]["horizontal_movement_m"] += 0.5
    elif bad == "native_truncated":
        src["native"]["complete_registry"] = False
    elif bad == "terminal_unknown":
        src["terminal"]["action_state"] = "unknown"
    elif bad == "wrong_action_ref":
        src["terminal"]["action_ref"] = "ATTACK"
    elif bad == "swapped_run":
        src["run_id"] = "stage-w1-other-run"
    elif bad == "next_event":
        src["source"]["next_probe_request_id"] = "s49-actual:wrong:event-888"
    elif bad == "unqualified_hold":
        src["native"]["after_bot_xyz"] = list(src["native"]["before_bot_xyz"])
        src["native"]["horizontal_movement_m"] = 0.0
        src["source"]["after_target_m"] = src["source"]["before_target_m"]
    elif bad == "post_seq_replay":
        src["source"]["next_probe_seq"] = src["source"]["after_seq"]
    elif bad == "source_sha_under_signed":
        src["source"]["before_health"] -= 1
    elif bad == "extra_archive_key":
        src["verified_by_minecraft"] = True
    raw = canonical(src)
    if bad == "noncanonical_bytes":
        raw += b"\n"
    archive = tmp_path/"foreign-source.json"
    archive.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()  # even with a freshly minted pin
    ledger = _new_ledger(tmp_path)
    with pytest.raises(StageWGateRejected):
        _consume(sample, ledger, archive_path=archive, archive_sha=sha)
    with sqlite3.connect(tmp_path/"spent.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)


def test_w1_no_overwrite_provisioned_ledger_and_no_live_authority(sample, tmp_path):
    path = (tmp_path/"spent.sqlite3").resolve()
    ledger = StageWPersistentGrantLedger.provision_new(path)
    with pytest.raises(StageWGateRejected):
        StageWPersistentGrantLedger.provision_new(path)
    result = _consume(sample, ledger)
    assert result.persistent_grant_reserved
    # Signer-private PEM and real S10 LearningUpdateAuthority never passed to
    # this consumer: the positive test remains only an OFFLINE reservation.
    assert not result.real_s10_commit_permitted
