"""B10: offline witnessed S15 issuer and SQLite replay regression controls."""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
)
from experiments.ac_b_b9_signed_s16 import (
    ExternalS16EvidenceGate,
    OfflineS16SourceIssuer,
    TrustedWorldEpoch,
    serialize_signed_evidence,
)
from experiments.ac_b_b10_source_journal import (
    DurableReadOnlyGate,
    ObservationBoundIssuer,
    ObservedS16Packet,
    PersistentReplayJournal,
    UnqualifiedWorldEvidence,
    run_offline_transaction,
)
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.provenance import Provenance
from test_action_feedback_qualification import (
    FakeSession,
    effect,
    issued_chain,
    observation,
    successful_session,
)


def origin() -> Provenance:
    return Provenance("b10-source-fixture", "observed")


def source_fixture():
    *_, binding, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)
    source_key = secrets.token_bytes(32)
    adapter = successful_session(command)
    packet = run_offline_transaction(
        issued, binding, adapter, source_key, origin(),
    )
    assert packet.consequence.status is WorldConsequenceStatus.EXECUTED
    assert len(adapter.sent) == 4
    return issued, binding, supervisor, command, packet, adapter, source_key


def fresh_gate(key, packet, path, *, revision=0):
    epoch = TrustedWorldEpoch(packet.consequence.session_id, revision)
    verifier = ExternalS16EvidenceGate(key, epoch)
    journal = PersistentReplayJournal(path)
    return DurableReadOnlyGate(verifier, journal)


def test_b10_issuer_executes_actual_s15_and_does_not_expose_arbitrary_sign():
    issued, binding, supervisor, command, packet, adapter, key = source_fixture()
    assert issued.state is ActionState.ISSUED
    assert packet.source_envelope.session_id == adapter.started.session_id
    assert packet.source_envelope.action_id == command.action_id
    assert packet.consequence.before_observation is not None
    assert packet.consequence.dispatch_receipt is not None
    assert packet.consequence.cleanup_receipt is not None
    assert packet.consequence.after_observation is not None
    assert packet.consequence.movement_distance > 0
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    issuer = ObservationBoundIssuer(key, adapter.started.session_id)
    assert not hasattr(issuer, "sign")
    assert not hasattr(issuer, "sign_consequence")
    assert not hasattr(issuer, "issue_action")


def test_atomic_local_replay_across_reopened_verifiers(tmp_path):
    issued, binding, supervisor, _, packet, _, key = source_fixture()
    journal = PersistentReplayJournal.initialize(tmp_path / "consumed.sqlite")
    first = DurableReadOnlyGate(
        ExternalS16EvidenceGate(key, TrustedWorldEpoch(packet.consequence.session_id, 0)),
        journal,
    )
    interpreted = first.qualify(issued, binding, packet)
    assert interpreted.disposition is ActionOutcomeDisposition.OUTCOME
    assert interpreted.reason_code == "observed_execution"
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    other = fresh_gate(key, packet, journal.path)
    with pytest.raises(UnqualifiedWorldEvidence, match="replay"):
        other.qualify(issued, binding, packet)
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_same_action_different_signed_event_cannot_bypass_replay(tmp_path):
    issued, binding, supervisor, _, packet, _, key = source_fixture()
    path = tmp_path / "journal.sqlite"
    PersistentReplayJournal.initialize(path)
    fresh_gate(key, packet, path).qualify(issued, binding, packet)
    alternate_signer = OfflineS16SourceIssuer(key, packet.consequence.session_id)
    alternate_signer.sign(packet.consequence)  # seq 1 same event as original
    another_receipt = alternate_signer.sign(packet.consequence)  # seq 2 distinct
    assert another_receipt.event_id != packet.source_envelope.event_id
    second = ObservedS16Packet(packet.consequence, another_receipt)
    with pytest.raises(UnqualifiedWorldEvidence, match="replay"):
        fresh_gate(key, packet, path).qualify(issued, binding, second)
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_threaded_simultaneous_consumers_only_one_wins(tmp_path):
    issued, binding, _, _, packet, _, key = source_fixture()
    path = tmp_path / "atomic.sqlite"
    PersistentReplayJournal.initialize(path)

    def attempt(_):
        try:
            fresh_gate(key, packet, path).qualify(issued, binding, packet)
        except UnqualifiedWorldEvidence:
            return False
        return True

    with ThreadPoolExecutor(max_workers=4) as executor:
        granted = list(executor.map(attempt, range(4)))
    assert sum(granted) == 1


def test_new_real_python_interpreter_sees_consumed_journal(tmp_path):
    issued, binding, supervisor, _, packet, _, key = source_fixture()
    path = tmp_path / "new-process.sqlite"
    PersistentReplayJournal.initialize(path)
    fresh_gate(key, packet, path).qualify(issued, binding, packet)
    raw_receipt = serialize_signed_evidence(packet.source_envelope)
    root = Path(__file__).resolve().parents[1]
    child = """
import asyncio
import json
import sys
from adapters.mineflayer.execution import build_mineflayer_command, execute_mineflayer_command
from experiments.ac_b_b10_source_journal import (
    DurableReadOnlyGate, ObservedS16Packet, PersistentReplayJournal,
)
from experiments.ac_b_b9_signed_s16 import (
    ExternalS16EvidenceGate, TrustedWorldEpoch, parse_signed_evidence,
)
from relay_self.provenance import Provenance
from test_action_feedback_qualification import issued_chain, successful_session

info=json.loads(sys.stdin.read())
*_, binding, _, supervisor, issued = issued_chain()[-4:]
command = build_mineflayer_command(issued,binding)
consequence = asyncio.run(execute_mineflayer_command(
    successful_session(command),command,
    provenance=Provenance("b10-source-fixture","observed")))
envelope = parse_signed_evidence(info["envelope"])
verifier=ExternalS16EvidenceGate(bytes.fromhex(info["key"]),
    TrustedWorldEpoch(consequence.session_id,0))
gate=DurableReadOnlyGate(verifier, PersistentReplayJournal(info["path"]))
try:
    gate.qualify(issued,binding,ObservedS16Packet(consequence,envelope))
except Exception as error:
    print(json.dumps({"denied": "replay" in str(error), "type":type(error).__name__}))
else:
    print(json.dumps({"denied":False,"type":"BAD_ALLOW"}))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(root), str(root / "src"), str(root / "tests"),
         env.get("PYTHONPATH", ""))
    )
    request = {"path": str(path), "key": key.hex(), "envelope": raw_receipt}
    result = subprocess.run(
        [sys.executable, "-c", child], input=json.dumps(request),
        text=True, capture_output=True, check=True, timeout=20, env=env,
    )
    assert json.loads(result.stdout)["denied"]
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_source_issuer_rejects_wrong_session_and_invalid_issued_action():
    issued, binding, supervisor, command, packet, _, key = source_fixture()
    alien = ObservationBoundIssuer(key, "another-session")
    with pytest.raises(UnqualifiedWorldEvidence, match="session"):
        asyncio.run(alien.execute_and_sign(
            issued, binding, successful_session(command), provenance=origin(),
        ))
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    assert packet.consequence.action_id == issued.action_id


@pytest.mark.parametrize("ordered_messages", [
    ("wrong-order",),
    ("duplicate-seq",),
    ("extra-unexpected",),
])
def test_observer_requires_ordered_native_messages(ordered_messages):
    *_, binding, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)
    k = secrets.token_bytes(32)
    if ordered_messages == ("wrong-order",):
        messages = (
            observation(1,0,0),
            effect(3,command.action_id,"set_control"),
            effect(2,command.cleanup_action_id,"clear_controls"),
            observation(4,0,.2),
        )
    elif ordered_messages == ("duplicate-seq",):
        messages = (
            observation(1,0,0),
            effect(2,command.action_id,"set_control"),
            effect(2,command.cleanup_action_id,"clear_controls"),
            observation(4,0,.2),
        )
    else:
        messages = (
            observation(0,0,0),
            observation(1,0,0),
            effect(2,command.action_id,"set_control"),
            effect(3,command.cleanup_action_id,"clear_controls"),
            observation(4,0,.2),
        )
    fixture = FakeSession(messages)
    issuer = ObservationBoundIssuer(k, fixture.started.session_id)
    with pytest.raises(UnqualifiedWorldEvidence):
        asyncio.run(issuer.execute_and_sign(
            issued, binding, fixture, provenance=origin(),
        ))
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_incomplete_adapter_and_undetermined_movement_cannot_be_signed():
    *_, binding, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued,binding)
    source_key = secrets.token_bytes(32)
    empty = FakeSession(())
    with pytest.raises(UnqualifiedWorldEvidence):
        asyncio.run(ObservationBoundIssuer(
            source_key, empty.started.session_id,
        ).execute_and_sign(issued,binding,empty,provenance=origin()))
    # Complete native protocol messages with zero displacement must remain
    # WorldConsequence.UNDETERMINED and are not promoted to signed EXECUTED.
    stationary = FakeSession((
        observation(1,0,0),
        effect(2,command.action_id,"set_control"),
        effect(3,command.cleanup_action_id,"clear_controls"),
        observation(4,0,0),
    ))
    with pytest.raises(UnqualifiedWorldEvidence):
        asyncio.run(ObservationBoundIssuer(
            source_key,stationary.started.session_id,
        ).execute_and_sign(issued,binding,stationary,provenance=origin()))
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_unverified_b7_dict_never_qualifies_as_packet(tmp_path):
    issued, binding, supervisor, _, packet, _, key = source_fixture()
    path=tmp_path/"strict.sqlite"
    PersistentReplayJournal.initialize(path)
    generic={"session":"b7-world","a":0,"b":1,"action":0,"success":True}
    with pytest.raises(UnqualifiedWorldEvidence,match="observation-bound"):
        fresh_gate(key,packet,path).qualify(issued,binding,generic)
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_wrong_secret_and_stale_epoch_do_not_consume_replay_journal(tmp_path):
    issued,binding,supervisor,_,packet,_,key=source_fixture()
    path=tmp_path/"source.sqlite"
    PersistentReplayJournal.initialize(path)
    with pytest.raises(UnqualifiedWorldEvidence):
        fresh_gate(secrets.token_bytes(32), packet, path).qualify(
            issued,binding,packet,
        )
    with pytest.raises(UnqualifiedWorldEvidence,match="epoch"):
        fresh_gate(key,packet,path,revision=1).qualify(issued,binding,packet)
    fresh_gate(key,packet,path).qualify(issued,binding,packet)
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_missing_and_corrupted_local_journal_are_fail_closed(tmp_path):
    issued,binding,supervisor,_,packet,_,key=source_fixture()
    missing=tmp_path/"not-created.sqlite"
    with pytest.raises(UnqualifiedWorldEvidence,match="missing"):
        PersistentReplayJournal(missing)
    with pytest.raises(UnqualifiedWorldEvidence):
        PersistentReplayJournal.initialize(missing.parent / "bogus" / "db.sqlite")
    path=tmp_path/"corrupt.sqlite"
    PersistentReplayJournal.initialize(path)
    path.write_bytes(b"invalid database file")
    with pytest.raises(UnqualifiedWorldEvidence):
        PersistentReplayJournal(path)
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_no_implicit_action_outcome_or_learning_from_signed_evidence(tmp_path):
    issued,binding,supervisor,_,packet,_,key=source_fixture()
    path=tmp_path/"read-only.sqlite"
    PersistentReplayJournal.initialize(path)
    old=supervisor.get(issued.action_id)
    interpreted=fresh_gate(key,packet,path).qualify(issued,binding,packet)
    assert interpreted.disposition is ActionOutcomeDisposition.OUTCOME
    assert supervisor.get(issued.action_id) is old
    assert old.state is ActionState.ISSUED
    assert not hasattr(interpreted, "learning_feedback")
    assert not hasattr(interpreted, "commit_habit")


def test_coherent_untrusted_adapter_messages_are_not_physical_attestation(tmp_path):
    """A lying adapter can produce consistent signed proof: physical origin UNKNOWN."""
    *_, binding, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)
    # These coordinates are INVENTED by this test: no physical Minecraft
    # session exists. All structured protocol checks will nevertheless pass.
    forged_but_coherent = FakeSession((
        observation(1, 100.0, 200.0),
        effect(2, command.action_id, "set_control"),
        effect(3, command.cleanup_action_id, "clear_controls"),
        observation(4, 100.0, 200.20),
    ))
    key = secrets.token_bytes(32)
    packet = run_offline_transaction(
        issued, binding, forged_but_coherent, key, origin(),
    )
    path = tmp_path / "untrusted-observer.sqlite"
    PersistentReplayJournal.initialize(path)
    qualified = fresh_gate(key, packet, path).qualify(issued, binding, packet)
    assert qualified.disposition is ActionOutcomeDisposition.OUTCOME
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    # Therefore protocol-observation + HMAC cannot certify physical origin.


def test_privileged_sqlite_file_rollback_defeats_local_replay_claim(tmp_path):
    """A hostile filesystem rollback needs a separate trusted anti-rollback root."""
    issued, binding, supervisor, _, packet, _, key = source_fixture()
    path = tmp_path / "rollback-limited.sqlite"
    PersistentReplayJournal.initialize(path)
    empty_journal_snapshot = path.read_bytes()
    first = fresh_gate(key, packet, path).qualify(issued, binding, packet)
    assert first.disposition is ActionOutcomeDisposition.OUTCOME
    with pytest.raises(UnqualifiedWorldEvidence, match="replay"):
        fresh_gate(key, packet, path).qualify(issued, binding, packet)
    # A privileged actor who can replace the whole SQLite DB can rewind the
    # journal. This test intentionally documents a FAILURE of external trust,
    # not a success of replay protection against a filesystem adversary.
    path.write_bytes(empty_journal_snapshot)
    second = fresh_gate(key, packet, path).qualify(issued, binding, packet)
    assert second == first
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
